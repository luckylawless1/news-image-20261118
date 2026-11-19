// Entry point for the make.fun bounty "Sum up 18 November's world news in
// one image" (news-image-20261118).
//
// The poster itself is composed ahead of time by compose.py (Python/Pillow)
// and committed as entry.png next to this file. This program simply copies
// those exact bytes to the output directory the grader points at with
// MAKEFUN_OUTPUT_DIR (default /output). Node 22, standard library only.

import { copyFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const source = join(here, "entry.png");
const outputDir = process.env.MAKEFUN_OUTPUT_DIR ?? "/output";

mkdirSync(outputDir, { recursive: true });
copyFileSync(source, join(outputDir, "entry.png"));
