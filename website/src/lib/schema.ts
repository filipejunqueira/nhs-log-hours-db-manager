// Schema gate (BUILD_NOTES §4): accept 1.x with minor >= 1.
// 1.0.x predates the audit and lacks span_ok/I6, which the integrity
// panel requires; anything non-1.x is a different contract entirely.
export function schemaSupported(version: string): boolean {
  const parts = version.split(".")
  const major = Number(parts[0])
  const minor = Number(parts[1])
  return major === 1 && Number.isInteger(minor) && minor >= 1
}
