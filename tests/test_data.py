TEST_MARKDOWN = """
## Summary

- Nearby Friends: mobile clients see nearby friends with updates every few seconds; prioritize low latency and eventual consistency.
- Core architecture: clients send periodic locations to WebSocket servers; latest locations live in a Redis location cache; historical data in a Location History DB.
- Fan-out: each user has a Redis Pub/Sub channel; WebSocket servers subscribe/publish to channels and forward filtered updates to connected clients.
- APIs: WebSocket for streaming (init + updates + subscribe/unsubscribe); REST for CRUD on users/friends.
- Scalability/reliability: stateless API servers; stateful WebSocket servers with draining; Redis Pub/Sub sharded via consistent hashing + service discovery; ephemeral messages with acceptable occasional data point

## Cues & Key Terms

- Low latency, eventual consistency: prioritize speed; tolerate slightly stale locations.
- TTL: per-user key expiry in Redis to drop inactive users automatically.
- WebSocket server (stateful): holds _connectionId_ maps and subscriptions; computes distance threshold for notifications.
- Location cache (Redis): `user_id -> [lat, long, timestamp]`; fast, non-durable; replicas for availability.
- Location history DB: `[user_id, lat, long, timestamp]`; RDBMS (sharded by `user_id`) or NoSQL.
- Channel per user: unique Redis Pub/Sub topic for each user.
- Service discovery: tracks active Pub/Sub servers; notifies WS servers; basis for consistent-hash ring.
- Consistent hashing (hash ring): maps channelIDs to Pub/Sub servers; smooth rebalancing during scale/replace.
- Draining: mark WS node “draining” to migrate connections before shutdown.
- Geohash channels: pool of region channels for “nearby random person.”

## Notes

- Requirements

    - Functional: show nearby friends on phones; refresh every few seconds.
    - Non-functional: low latency; reliability with occasional data point loss acceptable; eventual consistency for location store.
- High-level design

    `flowchart LR     MU["Mobile Users"] -- WebSocket (WS) --> LB["Load Balancer"]     MU -- HTTP --> LB     LB <--> WSS["WebSocket Servers"]     LB --> APIS["API Servers"]     WSS --> LC[("Location Cache")] & LHD[("Location History Database")] & RPS["Redis Pub/Sub"]     RPS --> WSS     APIS --> UD[("User Database")]     WSS --> UD      RPS@{ shape: h-cyl}      LC:::store      LHD:::store      RPS:::store      UD:::store`

    - Periodic location update (publish path)

        1. Mobile client sends location update to LB.

        2. LB forwards to a WebSocket server.

        3. WS saves to Location History DB.

        4. WS updates Location Cache (latest position).

        5. WS publishes new location to the user’s Redis Pub/Sub channel.

        6. Redis Pub/Sub broadcasts to subscribed WS servers.

        7. Each WS computes distance between publisher and its subscribed clients; maintains:

            - `Map<user, connectionId>`, `Map<user, location>`, and `{channelId: connectionIDs}`.
        8. If `distance < threshold`, WS forwards location + `lastUpdated` timestamp to client.

    - Client initialization (subscribe path)

        1. Client opens WS connection.
        2. Client requests initial nearby friends list.
        3. WS updates user’s location in cache and stores `connectionId`.
        4. WS loads user’s friends from User DB (sharded by `user_id`).
        5. WS batches reads from Location Cache for friends’ latest locations (TTL filters inactive).
        6. WS computes distance + returns `lastUpdatedTimestamp` per friend.
        7. WS subscribes to each friend’s Redis channel.
        8. WS publishes the user’s current location to the user’s channel.

        `flowchart TD  subgraph WSS1["WebSocket Servers"]         u1ws@{ label: "User 1's WS connection" }         u5ws@{ label: "User 5's WS connection" }   end  subgraph WSS2["WebSocket Servers"]         u2ws@{ label: "User 2's WS connection" }         u3ws@{ label: "User 3's WS connection" }         u4ws@{ label: "User 4's WS connection" }         u6ws@{ label: "User 6's WS connection" }   end  subgraph RPS["Redis Pub/Sub"]         ch1@{ label: "User 1's channel" }         ch5@{ label: "User 5's channel" }   end     u1["User 1"] --> u1ws     u5["User 5"] --> u5ws     u1ws -- Publish --> ch1     u5ws -- Publish --> ch5     ch1 -- Subscribe --> u2ws & u3ws & u4ws     ch5 -- Subscribe --> u4ws & u6ws     u2ws -- Friends' location update (4) --> u2["User 2"]     u3ws -- Friends' location update --> u3["User 3"]     u4ws -- Friends' location update --> u4["User 4"]     u6ws -- Friends' location update --> u6["User 6"]      u1ws@{ shape: subroutine}     u5ws@{ shape: subroutine}     u2ws@{ shape: subroutine}     u3ws@{ shape: subroutine}     u4ws@{ shape: subroutine}     u6ws@{ shape: subroutine}     ch1@{ shape: h-cyl}     ch5@{ shape: h-cyl}      u1:::phone      u5:::phone      u2:::phone      u3:::phone      u4:::phone      u6:::phone`

- API design

    - WebSocket:

        - _periodic_location_update_
        - _receive_location_updates_
        - _init_nearby_list_ (on startup)
        - _subscribe_friend_ / _unsubscribe_friend_
    - HTTP (REST): CRUD for users/friends/profile updates.

- Data model

    - Location Cache (Redis): `user_id -> [latitude, longitude, timestamp]`; TTL per key; easy to shard by `user_id`; replicas for availability; not durably stored.
    - Location History DB: append-only `[user_id, latitude, longitude, timestamp]`; RDBMS (sharded by `user_id`) or NoSQL.
- WebSocket servers

    - Stateful; fronted by LB.
    - Draining for node replacement: mark as “draining,” stop new conns, wait until enough clients disconnect, then take down.
    - Store connection and subscription maps as above.
- Redis Pub/Sub server(s)

    - Lightweight channel creation; channel exists when subscribed.
    - Tracks subscribers using compact in-memory structures (hash + linked list).
    - One unique channel per user; offline users cost minimal memory/CPU.
    - CPU is typical bottleneck; memory can handle millions of channels.
- Distributed Pub/Sub cluster

    - Shard channels across servers by `channel_id`.

    - Service discovery (e.g., ZooKeeper):

        - Keeps list of active Pub/Sub servers; simple API.
        - Notifies WS servers on membership changes.
    - Active servers arranged in a consistent-hash ring.

    - WS builds ring in memory, locates the responsible Pub/Sub server for each channel, then publishes/subscribes accordingly.

        `flowchart LR  subgraph RC["Redis Pub/Sub Cluster"]         ch1["Channel 1"]         ch2["Channel 2"]         ch3["Channel 3"]   end     WS["WebSocket Servers"] -- "1 | Consult hash ring" --> H["Hash Ring"]     WS -- "2 | Publish location update" --> ch2      ch1@{ shape: h-cyl}     ch2@{ shape: h-cyl}     ch3@{ shape: h-cyl}     H@{ shape: dbl-circ}`

- WS ↔ Pub/Sub interaction

    - Redis keeps subscriber lists (WS servers).
    - On channel update, Redis notifies relevant WS servers.
    - WS maps channelID → connectionIDs to know which clients to push.
- Scaling/operations for Pub/Sub

    - Messages are ephemeral (not persisted); forwarded or dropped—acceptable for this use case.

    - Because subscriber lists are stateful per Pub/Sub node, resizing requires:

        1. Determine new ring size.
        2. Update ring keys in service discovery; WS servers receive change, then issue re-subscriptions from old → new servers.
        3. Some updates may be missed during transition—acceptable.
    - Same re-subscription flow on server replacement.

- Adding/removing friends

    - Mobile client registers callbacks to notify WS of friend changes; WS subscribes/unsubscribes to corresponding channels.
- Users with many friends

    - Not a hotspot key at WS layer—subscribers spread across WS servers.
    - Pub/Sub hotspots mitigated by sharding; heavy users distributed across cluster.
- Nearby random person feature

    - Create Pub/Sub channels by geohash.
    - Users publish to their geohash channel and subscribe to their geohash + 8 neighboring cells.
    - Alternative tech: Erlang-based messaging (e.g., WhatsApp) could replace Redis Pub/Sub.
- Chapter Summary

    ```
    flowchart LR     NF["Nearby Friends"] --> S1["Step 1"] & S2["Step 2"] & S3["Step 3"] & S4["Step 4"]     S1 --> FR["Functional requirements"] & NFR["Non-functional requirements"] & EST["Estimation"]     FR --> FR1["View nearby friends"] & FR2["Update nearby friend list"]     NFR --> LAT["Low latency"]     EST --> RADIUS["5-mile radius"] & REFRESH["Location refresh interval: 30s"] & QPS["Location update QPS: 334k"]     S2 --> HLD["High-level design"] & PERIODIC["Periodic location update"] & API["API design"] & DM["Data model"]     HLD --> R1["RESTful API servers"] & WSS["WebSocket servers"] & RLC["Redis location cache"] & LHD["Location history database"] & RPS["Redis Pub/Sub server"]     DM --> DMC1["Location cache"] & DMC2["Location history database"]     S3 --> SEC["Scale each component"] & ARF["Adding/removing friends"] & UWMF["Users with many friends"] & NRP["Nearby random person"]     SEC --> SEC1["API servers"] & SEC2["WebSocket servers"] & SEC3["User database"] & SEC4["Location cache"] & SEC5["Redis Pub/Sub server"] & SEC6["Alternative to Redis Pub/Sub"]     S4 --> W["Wrap Up"]      NF@{ shape: rounded}
    ```
"""

TEST_DUE_NOTES = {
    "object": "list",
    "results": [
        {
            "object": "page",
            "id": "25d14afe-aadd-8162-a265-fdd585fb3871",
            "created_time": "2025-08-28T11:08:00.000Z",
            "last_edited_time": "2025-08-28T19:40:00.000Z",
            "created_by": {
                "object": "user",
                "id": "d69f2f08-9286-464f-b3d0-00024efc14a8",
            },
            "last_edited_by": {
                "object": "user",
                "id": "3be956fa-1497-4111-af14-35ab0d1239a5",
            },
            "cover": None,
            "icon": None,
            "parent": {
                "type": "database_id",
                "database_id": "24714afe-aadd-8010-835f-e9ac2a690ed7",
            },
            "archived": False,
            "in_trash": False,
            "properties": {
                "Resource Tag": {
                    "id": "%3AC%3FP",
                    "type": "select",
                    "select": {
                        "id": "?^<h",
                        "name": "System Design Interview - Volume II",
                        "color": "brown",
                    },
                },
                "Log Revision": {"id": "%3CzN%3B", "type": "button", "button": {}},
                "Next Review": {
                    "id": "A%3A~h",
                    "type": "formula",
                    "formula": {
                        "type": "date",
                        "date": {
                            "start": "2025-08-29",
                            "end": None,
                            "time_zone": None,
                        },
                    },
                },
                "Created Date": {
                    "id": "%5CE%5Cb",
                    "type": "date",
                    "date": {"start": "2025-08-28", "end": None, "time_zone": None},
                },
                "Revisions": {"id": "lpVV", "type": "number", "number": 0},
                "Last Review": {
                    "id": "uEKu",
                    "type": "date",
                    "date": {"start": "2025-08-28", "end": None, "time_zone": None},
                },
                "Name": {
                    "id": "title",
                    "type": "title",
                    "title": [
                        {
                            "type": "text",
                            "text": {
                                "content": "Chapter 2: Nearby Friends",
                                "link": None,
                            },
                            "annotations": {
                                "bold": False,
                                "italic": False,
                                "strikethrough": False,
                                "underline": False,
                                "code": False,
                                "color": "default",
                            },
                            "plain_text": "Chapter 2: Nearby Friends",
                            "href": None,
                        }
                    ],
                },
            },
            "url": "https://www.notion.so/Chapter-2-Nearby-Friends-25d14afeaadd8162a265fdd585fb3871",
            "public_url": None,
        },
        {
            "object": "page",
            "id": "25314afe-aadd-81d6-9e85-c752588bc0ae",
            "created_time": "2025-08-18T18:20:00.000Z",
            "last_edited_time": "2025-08-22T15:58:00.000Z",
            "created_by": {
                "object": "user",
                "id": "d69f2f08-9286-464f-b3d0-00024efc14a8",
            },
            "last_edited_by": {
                "object": "user",
                "id": "3be956fa-1497-4111-af14-35ab0d1239a5",
            },
            "cover": None,
            "icon": None,
            "parent": {
                "type": "database_id",
                "database_id": "24714afe-aadd-8010-835f-e9ac2a690ed7",
            },
            "archived": False,
            "in_trash": False,
            "properties": {
                "Resource Tag": {
                    "id": "%3AC%3FP",
                    "type": "select",
                    "select": {
                        "id": "870c2c96-660a-439b-8420-0d0946c65c6d",
                        "name": "System Design Interview - Volume I",
                        "color": "orange",
                    },
                },
                "Log Revision": {"id": "%3CzN%3B", "type": "button", "button": {}},
                "Next Review": {
                    "id": "A%3A~h",
                    "type": "formula",
                    "formula": {
                        "type": "date",
                        "date": {
                            "start": "2025-08-29",
                            "end": None,
                            "time_zone": None,
                        },
                    },
                },
                "Created Date": {
                    "id": "%5CE%5Cb",
                    "type": "date",
                    "date": {"start": "2025-08-18", "end": None, "time_zone": None},
                },
                "Revisions": {"id": "lpVV", "type": "number", "number": 2},
                "Last Review": {
                    "id": "uEKu",
                    "type": "date",
                    "date": {"start": "2025-08-22", "end": None, "time_zone": None},
                },
                "Name": {
                    "id": "title",
                    "type": "title",
                    "title": [
                        {
                            "type": "text",
                            "text": {
                                "content": "Chapter 15: Design Google Drive",
                                "link": None,
                            },
                            "annotations": {
                                "bold": False,
                                "italic": False,
                                "strikethrough": False,
                                "underline": False,
                                "code": False,
                                "color": "default",
                            },
                            "plain_text": "Chapter 15: Design Google Drive",
                            "href": None,
                        }
                    ],
                },
            },
            "url": "https://www.notion.so/Chapter-15-Design-Google-Drive-25314afeaadd81d69e85c752588bc0ae",
            "public_url": None,
        },
        {
            "object": "page",
            "id": "25014afe-aadd-81f8-88bb-d4e7516d111c",
            "created_time": "2025-08-15T14:30:00.000Z",
            "last_edited_time": "2025-08-22T15:44:00.000Z",
            "created_by": {
                "object": "user",
                "id": "d69f2f08-9286-464f-b3d0-00024efc14a8",
            },
            "last_edited_by": {
                "object": "user",
                "id": "3be956fa-1497-4111-af14-35ab0d1239a5",
            },
            "cover": None,
            "icon": None,
            "parent": {
                "type": "database_id",
                "database_id": "24714afe-aadd-8010-835f-e9ac2a690ed7",
            },
            "archived": False,
            "in_trash": False,
            "properties": {
                "Resource Tag": {
                    "id": "%3AC%3FP",
                    "type": "select",
                    "select": {
                        "id": "870c2c96-660a-439b-8420-0d0946c65c6d",
                        "name": "System Design Interview - Volume I",
                        "color": "orange",
                    },
                },
                "Log Revision": {"id": "%3CzN%3B", "type": "button", "button": {}},
                "Next Review": {
                    "id": "A%3A~h",
                    "type": "formula",
                    "formula": {
                        "type": "date",
                        "date": {
                            "start": "2025-08-29",
                            "end": None,
                            "time_zone": None,
                        },
                    },
                },
                "Created Date": {
                    "id": "%5CE%5Cb",
                    "type": "date",
                    "date": {"start": "2025-08-15", "end": None, "time_zone": None},
                },
                "Revisions": {"id": "lpVV", "type": "number", "number": 2},
                "Last Review": {
                    "id": "uEKu",
                    "type": "date",
                    "date": {"start": "2025-08-22", "end": None, "time_zone": None},
                },
                "Name": {
                    "id": "title",
                    "type": "title",
                    "title": [
                        {
                            "type": "text",
                            "text": {
                                "content": "Chapter 11: Design A News Feed System",
                                "link": None,
                            },
                            "annotations": {
                                "bold": False,
                                "italic": False,
                                "strikethrough": False,
                                "underline": False,
                                "code": False,
                                "color": "default",
                            },
                            "plain_text": "Chapter 11: Design A News Feed System",
                            "href": None,
                        }
                    ],
                },
            },
            "url": "https://www.notion.so/Chapter-11-Design-A-News-Feed-System-25014afeaadd81f888bbd4e7516d111c",
            "public_url": None,
        },
        {
            "object": "page",
            "id": "24914afe-aadd-818c-affb-f0632923d1f7",
            "created_time": "2025-08-08T13:53:00.000Z",
            "last_edited_time": "2025-08-25T19:26:00.000Z",
            "created_by": {
                "object": "user",
                "id": "d69f2f08-9286-464f-b3d0-00024efc14a8",
            },
            "last_edited_by": {
                "object": "user",
                "id": "3be956fa-1497-4111-af14-35ab0d1239a5",
            },
            "cover": None,
            "icon": None,
            "parent": {
                "type": "database_id",
                "database_id": "24714afe-aadd-8010-835f-e9ac2a690ed7",
            },
            "archived": False,
            "in_trash": False,
            "properties": {
                "Resource Tag": {
                    "id": "%3AC%3FP",
                    "type": "select",
                    "select": {
                        "id": "870c2c96-660a-439b-8420-0d0946c65c6d",
                        "name": "System Design Interview - Volume I",
                        "color": "orange",
                    },
                },
                "Log Revision": {"id": "%3CzN%3B", "type": "button", "button": {}},
                "Next Review": {
                    "id": "A%3A~h",
                    "type": "formula",
                    "formula": {
                        "type": "date",
                        "date": {
                            "start": "2025-08-30",
                            "end": None,
                            "time_zone": None,
                        },
                    },
                },
                "Created Date": {
                    "id": "%5CE%5Cb",
                    "type": "date",
                    "date": {"start": "2025-08-08", "end": None, "time_zone": None},
                },
                "Revisions": {"id": "lpVV", "type": "number", "number": 2},
                "Last Review": {
                    "id": "uEKu",
                    "type": "date",
                    "date": {"start": "2025-08-23", "end": None, "time_zone": None},
                },
                "Name": {
                    "id": "title",
                    "type": "title",
                    "title": [
                        {
                            "type": "text",
                            "text": {
                                "content": "Chapter 4: Design A Rate Limiter",
                                "link": None,
                            },
                            "annotations": {
                                "bold": False,
                                "italic": False,
                                "strikethrough": False,
                                "underline": False,
                                "code": False,
                                "color": "default",
                            },
                            "plain_text": "Chapter 4: Design A Rate Limiter",
                            "href": None,
                        }
                    ],
                },
            },
            "url": "https://www.notion.so/Chapter-4-Design-A-Rate-Limiter-24914afeaadd818caffbf0632923d1f7",
            "public_url": None,
        },
    ],
    "next_cursor": None,
    "has_more": False,
    "type": "page_or_database",
    "page_or_database": {},
    "request_id": "60e33121-0942-4a0e-9ffd-c0901149f5c3",
}


TEST_LLM_QUIZ = {
    "questions": [
        {
            "id": "q001",
            "text": "What two priorities are emphasized for Nearby Friends in the Summary?",
            "difficulty": "easy",
            "type": "short_answer",
            "section_refs": ["H1: Summary"],
            "skills": ["recall"],
        },
        {
            "id": "q002",
            "text": "According to the Core architecture, where are the latest locations stored and where is the historical data stored?",
            "difficulty": "easy",
            "type": "short_answer",
            "section_refs": ["H1: Summary"],
            "skills": ["recall"],
        },
        {
            "id": "q003",
            "text": "What do WebSocket servers do when they receive a location update from Redis Pub/Sub?",
            "difficulty": "medium",
            "type": "short_answer",
            "section_refs": ["H1: Summary"],
            "skills": ["understand"],
        },
        {
            "id": "q004",
            "text": "What Redis mechanism is used to drop inactive users automatically?",
            "difficulty": "easy",
            "type": "short_answer",
            "section_refs": ["H2: Cues & Key Terms"],
            "skills": ["recall"],
        },
        {
            "id": "q005",
            "text": "What is the Redis Location Cache mapping for a user?",
            "difficulty": "easy",
            "type": "short_answer",
            "section_refs": ["H2: Cues & Key Terms"],
            "skills": ["recall"],
        },
        {
            "id": "q006",
            "text": "How does the system locate the responsible Pub/Sub server for each channel in the cluster after scaling?",
            "difficulty": "hard",
            "type": "short_answer",
            "section_refs": ["H2: Cues & Key Terms"],
            "skills": ["analyze"],
        },
        {
            "id": "q007",
            "text": "What is the purpose of draining a WebSocket server?",
            "difficulty": "easy",
            "type": "short_answer",
            "section_refs": ["H2: Cues & Key Terms"],
            "skills": ["recall"],
        },
        {
            "id": "q008",
            "text": "How are Pub/Sub channels created for the nearby random person feature and how do users subscribe?",
            "difficulty": "easy",
            "type": "short_answer",
            "section_refs": ["H2: Cues & Key Terms"],
            "skills": ["understand"],
        },
        {
            "id": "q009",
            "text": "What are the two storage options mentioned for the Location History DB?",
            "difficulty": "easy",
            "type": "short_answer",
            "section_refs": ["H2: Cues & Key Terms"],
            "skills": ["recall"],
        },
        {
            "id": "q010",
            "text": "Name two WebSocket API types used in this design.",
            "difficulty": "easy",
            "type": "short_answer",
            "section_refs": ["H3: Notes"],
            "skills": ["recall"],
        },
    ]
}


TEST_EVALUATION_RESPONSE = """
Question 1
- Student answer:
  1) Should be able to find nearby friends
  2) Low latency
- Evaluation: Partially Correct
- Why:
  - The notes state two priorities: low latency and eventual consistency.
  - “Should be able to find nearby friends” is a functional requirement, not a stated
priority.
  - The missing priority is eventual consistency (and the note mentions updates every
few seconds, but emphasizes latency and eventual consistency as the design priorities).

Question 2
- Student answer:
  latest locations: Redis Cache
  historical data: RDBMS or NoSQL DB
- Evaluation: Correct
- Why:
  - The Core architecture places latest locations in a Redis location cache, and
historical data in a Location History DB (which can be an RDBMS or NoSQL). Your wording
matches this structure.

Question 3
- Student answer:
  Notify the relevant user about the new friend.
- Evaluation: Incorrect
- Why:
  - According to the notes, when a location update arrives via Redis Pub/Sub, the Redis
Pub/Sub broadcasts to subscribed WebSocket servers. Each WebSocket server maintains maps
of connections and subscriptions, computes distance to determine which connected clients
should receive the update, and forwards the location plus lastUpdated timestamp to those
clients if the distance threshold is met. It’s not simply “notify the relevant user
about the new friend.”

Summary Section
- Key gaps observed:
  - Missed the explicit two design priorities: low latency and eventual consistency.
  - Inadequate description of WebSocket server behavior regarding Pub/Sub broadcasts and
distance-based forwarding.
- 2–3 areas to review:
  - Review the two design priorities for Nearby Friends (low latency and eventual
consistency) and how updates every few seconds support them.
  - Review the data flow: Redis as the Location Cache for latest positions, Location
History DB for history, and how Pub/Sub broadcasts are handled by WebSocket servers,
including per-connection mapping and the distance-threshold forwarding logic.
  - Review the WS/Pub/Sub interaction details: channel per user, how updates are
propagated to the right WebSocket servers, and how proximity filtering (distance <
threshold) decides forwardings.
- Notion page for further reading:
  Notion page URL: (URL not provided in the input)
"""

"""
Should be able to find nearby friends
Low latency

latest locations: Redis Cache
historical data: RDBMS or NoSQL DB

Notify the relevant user about the new friend.
"""


TEST_MARKDOWN_NOTES = """
# Summary
- Map systems rely on projections, geocoding, geohashes, and tiled rendering; clients fetch only the tiles needed for the current zoom and view.
- Routing uses routing tiles (multiple detail levels) and shortest-path algorithms (A* or Dijkstra) combined with ETA prediction and ranking to pick the best route.
- A service-oriented design separates Location, Navigation, Geocoding, Route Planner, Shortest-Path, ETA, Ranker, and Updater services; tiles and routing data are heavily cached/CDN-backed.
- Scale requires pre-generated tiles, geohash addressing, write-optimized storage (e.g., Cassandra), streaming via a message queue, and aggressive caching in S3/CDN.
- Adaptive ETA and re-routing track active users and push updates via efficient delivery protocols (prefer websockets for bidirectional comms).

# Cues & Key Terms
- Map projection (Web Mercator): Converting the 3D globe to a 2D plane for maps.
- Geocoding: Converting an address to latitude/longitude.
- Reverse geocoding: Converting latitude/longitude to a human-readable address.
- Geohash: Short string encoding of a geographic area; used to key tiles and grids.
- Tiling: Splitting the world into map image tiles per zoom level; client fetches relevant tiles.
- Routing tiles: Grid cells for routing; each references neighbors it connects to; exist at multiple detail levels (local, arterial, highways).
- A*/Dijkstra: Graph shortest-path algorithms; intersections are nodes, roads are edges.
- Adjacency list: Graph representation used to store routing data efficiently.
- CDN/S3: Object storage and content delivery for precomputed map tiles.
- Cassandra: Example of a write-heavy, horizontally scalable store for user location history.
- ETA service: Machine learning-based prediction of travel time for candidate routes.
- Kafka/message queue: Stream user location updates for downstream processors.
- WebSocket vs SSE/long polling: Prefer WebSocket for lower footprint and bidirectional updates.

# Notes
- Chapter 3: Google Maps

- Requirements
  - Functional
    - user location update
    - navigation, including ETA
    - map rendering
  - Non-functional
    - accuracy; give right directions
    - smooth navigation
    - optimize for data and battery usage
    - availability and scalability

- Maps 101
  - Map projection: translating points from a 3D globe to a 2D plane; maps use Web Mercator.
  - Geocoding: process of converting addresses to geographic coordinates.
  - Reverse geocoding: converting coordinates (lat/long) to a human-readable address.
  - One way to geocode is interpolation; uses data from sources like geographic information systems (GIS).
  - Geohashing: encodes a geographic area into a short string of letters and digits.
  - Map rendering
    - Tiling: world is broken into multiple tiles; client downloads relevant tiles to render the map.
      - Distinct sets of tiles at different zoom levels.
      - Client chooses the set of relevant tiles based on zoom level.
  - Routing
    - Dijkstra’s or A*
    - intersections are nodes; roads are edges of the graph

- Routing tiles
  - Since the map of the complete world would be huge, divide the world into small grids for routing; these grids are called routing tiles.
  - Each routing tile holds references to all other tiles it connects to.
  - Three sets of routing tiles with different levels of detail
    - Most detailed → contain local roads
    - Intermediate level → arterial roads connecting districts
    - Lowest detail → contain major highways

- Back-of-the-envelope estimation
  - Total zoom levels = 24; number of tiles at zoom level 24 ≈ 4.7 trillion.
  - Assume each image is 10 KB; total space required = 44 PB.
  - 90% of world is uninhabited → storage required = ?? PB (value unclear in notes).
  - The number of tiles between zoom levels differs by a factor of 4.
    - -> Total storage required = 50 + 50/4 + 50/16 + … = 67 PB.
    - -> Rough estimate = 100 PB.
  - DAU = 1 billion; every user uses navigation 35 mins per week.
  - -> 35 billion mins per day; -> 5 billion min/day.
  - (5 billion × 60)/(24 × 3600) ≈ 3 million QPS.
  - Assume GPS updates are batched and sent every 15 seconds → QPS = 3 million / 15 = 200,000.
  - -> Peak QPS = 5× = 1 million.

- High-level Design (Fig 3.7)
  - Location service
    - Responsible for recording users’ location updates.
    - Stream of location data can be used to improve service over time.
    - Data can be used to provide ETA estimates.
    - Location history can be buffered on the client and sent in batch to the server.
    - DB required to support high-write volume; e.g., Cassandra.
    - Use HTTP keepalive.
  - Navigation service
    - Responsible for finding reasonably fast route from point A to point B.
  - Map rendering
    - Map tiles are fetched from server on-demand.
    - New files are fetched when
      - user is zooming and panning the map viewpoint
      - during navigation when user moves out of current map into a nearby tile
    - To serve the data efficiently (options)
      - (1) Server builds the tiles on the fly
        - puts too much load on the server
        - cannot take advantage of caching
      - (2) Serve pre-generated set of map tiles at each zoom level
        - each tile represented by its geohash
        - client determines the geohash and fetches the data from CDN
        - this option is preferred
      - We encode grids in geohash; unique geohash per grid.
        - easy to calculate geohash on the client based on lat/long
        - to further optimize, have a separate service to convert a lat/long pair and zoom level to a URL; avoids hardcoding logic on client side (Fig 3.12)

- Tile generation options comparison

Option | Pros | Cons
---|---|---
Build tiles on the fly | Flexible | Puts too much load on server; cannot leverage caching
Serve pre-generated tiles | Fetch via CDN by geohash; cache-friendly; preferred | Requires preprocessing and storage

- High-level architecture (diagram)

```mermaid
flowchart LR
  User[Mobile/Web Client] -- tiles via URL/geohash --> CDN[(CDN)]
  CDN --> S3Tiles[(S3: Precomputed Tiles)]

  User -- location updates --> APIGW[API Gateway]
  APIGW --> LocSvc[Location Service]
  APIGW --> NavSvc[Navigation Service]

  LocSvc --> Cassandra[(Cassandra: Location History)]
  LocSvc --> MQ[(Message Queue/Kafka)]

  MQ --> Updaters[Updater Services]
  Updaters --> TrafficDB[(Traffic DB)]
  Updaters --> RoutingTiles[(Routing Tiles in S3/Cache)]

  NavSvc --> Geocode[Geocoding Service]
  Geocode --> PlacesDB[(Key-Value Geocoding DB)]

  NavSvc --> RoutePlanner[Route Planner]
  RoutePlanner --> Shortest[Shortest-Path Service]
  Shortest --> RoutingTiles
  RoutePlanner --> ETA[ETA Service]
  RoutePlanner --> Ranker[Ranker Service]
  Ranker --> NavSvc
```

- Design Deep Dive
  - Data model
    - Routing tiles
      - initial data obtained from different sources and authorities
      - raw data not organised as a graph
      - run periodic offline processing pipelines (routing tiles processing service) to transform this data into routing tiles
      - each tile contains a list of graph nodes (intersections) and roads (edges); also contains references to other tiles its roads connect to
      - most graph data is represented as adjacency list
      - efficient way to store → serialize data in adjacency list; store in S3; cache aggressively

- User location data (valuable)
  - update road data & routing tiles using user location data
  - other uses
    - build a DB of live and historical traffic data
    - consumed by multiple data streams to update map data
  - write-heavy workload; horizontal scalability required; Cassandra is a good choice
  - sample DB entry contains: user-id, timestamp, location, etc.

- Geocoding Database
  - stores places and their lat/long pair
  - key-value store like Redis
  - use it to convert an origin or destination to lat/lng pair

- Pre-computed images of world map
  - pre-compute images at different zoom levels and store them in CDN, backed by S3

- Services
  - Location Service (Fig 3.11)
    - used to store user location data
    - a NoSQL key-value DB or a column-oriented DB would be a good choice
    - prioritise availability over consistency; new updates are more important than old updates
    - for DB configuration, use primary key as a combination of (user-id, timestamp)
      - Partition key → user-id
      - Sort-key → timestamp
    - Uses of location data
      - detect new or recently closed roads
      - improve accuracy of our map over time
      - input for live traffic
    - To support multiple use-cases; in addition to writing user location data to DB; also publish this info into a message queue, which can be consumed by other services (Fig 3.15)

- Rendering map
  - Different sets of precomputed tiles at different zoom levels
  - Google Maps uses 21 zoom levels
  - Level 0 → most zoomed out level → entire map represented by a single tile of 256×256
  - With each increment of zoom level, the number of tiles increases by 4× → level 1 would have 4 tiles and so on
  - One potential improvement is to use vector images like SVG; vector data compresses much better than images; bandwidth saving is substantial; provides a much better zooming experience

- Navigation service (Fig 3.21)
  - responsible for finding the fastest routes
  - Geocoding service
    - resolves an address to a lat/lng pair
    - navigation services call this service to geocode origin and destination before passing lat/lng pairs downstream
  - Route planner service
    - computes a suggested route that is optimized for travel time according to current traffic conditions
  - Shortest-path service
    - receives the origin and destination in lat/lng pairs and returns top-k shortest paths without considering traffic or current conditions
    - only depends on the structure of roads; caching can be beneficial
    - Runs a variation of A* algo
      - (1) The lat/lng points are converted to geohashes, which are used to load tiles (routing) for start and end points
      - (2) Starts from origin routing tile, traverses the graph data structure and fetches neighboring tiles from cache or object store as required; until a set of best routes is found
  - ETA service
    - route planner receives a list of possible shortest paths; it calls ETA service
    - ETA service uses ML to predict ETAs for each possible route
  - Ranker service
    - after receiving ETA info, route planner calls ranker service
    - applies possible filters as defined by the user
    - ranks possible routes from fastest to slowest and returns top-k results
  - Updater services
    - tap into Kafka streams or location updates and asynchronously update DBs like traffic DB and routing tiles

- Adaptive ETA and Re-routing
  - keep track of active navigating users and update them on ETA changes
  - for each actively navigating user, keep the current tile, the routing tile at route resolution, until user’s origin and destination lie in the same routing tile
  - now to check if a user is impacted by traffic change, only need to check if a routing tile is inside the last routing tile of the user
  - keep track of all possible routes for a navigating user, recalculate the ETA regularly and notify users if a new route with a shorter ETA is found

- Delivery protocols
  - options are push notification, long polling, websocket and server-sent events (SSE)
  - push notification → payload size is very limited
  - websocket is better than long polling as its server footprint is lower
  - websocket vs SSE → websocket is better as it offers bidirectional communication
"""
