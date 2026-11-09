// Buttons per episode. Script actions build an argv, AI actions build a prompt.
// Prompts follow planning/MODEL-TIERS.md.
import path from 'node:path';

const v = (ep) => `videos/${ep}`;
const epName = (ep) => `Ep ${parseInt(ep, 10)}`;
const tele = (ep, only, out) =>
  `python3 series/rust-in-ai/md_to_teleprompter.py ${v(ep)}/01-script/script.md "${epName(ep)}" ${v(ep)}/01-script/${out} --only ${only}`;

export const ACTIONS = [
  // [C] scripts, no AI
  { id: 'dry-run', engine: 'script', tier: 'C', label: 'Dry run shot plan', requires: 'shots', hint: 'post_record.py --dry-run',
    argv: (ep) => ['python3', 'tools/post_record.py', v(ep), '--dry-run'] },
  { id: 'post-record', engine: 'script', tier: 'C', label: 'Build first cut', requires: 'shots', hint: 'post_record.py on the recordings',
    confirm: 'Runs the full build (transcribe, takes, sync, grade, assemble, graphics). Can take a long time.',
    argv: (ep) => ['python3', 'tools/post_record.py', v(ep)] },
  { id: 'teleprompters', engine: 'script', tier: 'C', label: 'Rebuild teleprompters', requires: 'script', hint: 'cam + voice pages from script.md',
    argv: (ep) => ['zsh', '-c', `${tele(ep, 'cam', 'teleprompter-cam.html')} && ${tele(ep, 'read', 'teleprompter-voice.html')}`] },
  { id: 'contact-sheet', engine: 'script', tier: 'C', label: 'Contact sheet', hint: 'of the selected video file', needs: 'video',
    argv: (ep, file) => {
      const out = `${v(ep)}/03-edit/sheets/${path.parse(file).name}-sheet.png`;
      return ['zsh', '-c', 'mkdir -p "$(dirname "$2")" && ffmpeg -hide_banner -y -i "$1" -vf "fps=1/10,scale=320:-1,tile=6x5" -frames:v 1 "$2"', '_', file, out];
    } },
  { id: 'grade', engine: 'script', tier: 'C', label: 'Colour grade clip', hint: 'series-standard → 03-edit/processed', needs: 'video',
    argv: (ep, file) => ['./color-grading/preprocess.sh', '--outdir', `${v(ep)}/03-edit/processed`, file] },

  // [A] Claude
  { id: 'write-script', engine: 'claude', tier: 'A', label: 'Write script package', hint: 'script, shot list, proof, demos, teleprompters',
    prompt: (ep) => `Write the script for video ${ep} from its row in planning/BOARD.md, like 008: script, shot list, proof screenshots, terminal demos, teleprompters, RECORD-STEPS. Update STATUS.md and the board row.` },
  { id: 'shots', engine: 'claude', tier: 'A', label: 'shots.json + dry run', requires: 'script', hint: 'shot plan before recording',
    prompt: (ep) => `Write shots.json for video ${ep} from its 03-edit/shot-list.md and run the dry run. Report what needs my eye.` },
  { id: 'aip-finish', engine: 'claude', tier: 'A', label: 'AI Producer finish', requires: 'build', hint: 'after post_record, gives review link',
    prompt: (ep) => `Video ${ep}: build is done. Do the AI Producer finish from ${v(ep)}/03-edit/build/ and give me the review link. Update STATUS.md and the board row.` },
  { id: 'fact-check', engine: 'claude', tier: 'A', label: 'Fact-check numbers', requires: 'script', hint: 'against source pages, capture proof',
    prompt: (ep) => `Check every number in ${ep}'s script against its source, capture proof.` },
  { id: 'export', engine: 'claude', tier: 'A', label: 'Export + thumbnail', hint: 'final render to 04-export',
    confirm: 'Export the final video and make the thumbnail?',
    prompt: (ep) => `Export ${ep} and make the thumbnail.` },

  // [B] Antigravity
  { id: 'publish-copy', engine: 'agy', tier: 'B', label: 'Titles, description, chapters', requires: 'script', hint: '→ 04-export/description.md',
    prompt: (ep) => `From ${v(ep)}/01-script/script.md write 3 titles under 60 characters, a YouTube description with chapters (use the Part headings and their target times), and 15 tags. Save to ${v(ep)}/04-export/description.md. Read only that script file.` },
  { id: 'spelling', engine: 'agy', tier: 'B', label: 'Spelling check', requires: 'script', hint: 'against vocabulary.txt',
    prompt: (ep) => `Check ${v(ep)}/01-script/script.md against series/rust-in-ai/vocabulary.txt and list wrong spellings only. Do not edit files.` },
  { id: 'shorts', engine: 'agy', tier: 'B', label: 'Shorts ideas', requires: 'script', hint: '3 standalone 30–50 s parts',
    prompt: (ep) => `From ${v(ep)}/01-script/script.md pick 3 parts of 30 to 50 seconds that work alone as Shorts. List the line ranges and a hook line for each. Do not edit files.` },
];

export const publicActions = () =>
  ACTIONS.map(({ id, engine, tier, label, hint, confirm, needs, requires }) => ({ id, engine, tier, label, hint, confirm, needs, requires }));
