import { Chip } from "./ui";
import { LEVEL_META, LEVEL_TONE } from "../utils/status";

// Kept so older imports of StatusDot keep working.
export default function StatusDot({ status }) {
  const level = status === "severe" || status === "chronic" ? "high" : LEVEL_META[status] ? status : "normal";
  return <Chip tone={LEVEL_TONE[level]}>{status === "chronic" ? "Chronic" : LEVEL_META[level].label}</Chip>;
}
