#!/usr/bin/env node
import { readFileSync } from "node:fs";
import { stdin as input } from "node:process";
import { markdownToBlocks } from "@tryfabric/martian";

async function readStdin() {
  return await new Promise((resolve, reject) => {
    let buf = "";
    input.setEncoding("utf8");
    input.on("data", (c) => (buf += c));
    input.on("end", () => resolve(buf));
    input.on("error", reject);
  });
}

async function main() {
  const args = process.argv.slice(2);
  let md;

  if (args[0] && args[0] !== "--stdin") {
    md = readFileSync(args[0], "utf8");
  } else {
    md = await readStdin();
  }

  const options = {
    enableEmojiCallouts: process.env.MARTIAN_EMOJI_CALLOUTS === "1",

    // Set MARTIAN_STRICT_IMAGE_URLS=1 to force external image blocks even for invalid URLs.
    strictImageUrls: process.env.MARTIAN_STRICT_IMAGE_URLS === "1",

    // Martian handles Notion limits by truncating/splitting; you can disable truncation:
    notionLimits: {
      truncate: process.env.MARTIAN_TRUNCATE === "0" ? false : true,
      onError: (err) => {
        // surfaced on stderr; Python shim will include this if the run fails
        console.error(err.message || String(err));
      }
    }
  };

  const blocks = markdownToBlocks(md, options); 
  process.stdout.write(JSON.stringify(blocks));
}

main().catch((e) => {
  console.error(e && e.stack ? e.stack : String(e));
  process.exit(1);
});