const suspiciousPattern = /(?:Ã|Â|Æ|Ð|Ñ|Ø|æ|ç|è|é|ê|ë|ì|í|î|ï|ð|ñ|ò|ó|ô|ö|ø|ù|ú|û|ü|ý|þ|ÿ|€™|œ|š|ž|�)/;
const cjkPattern = /[\u3400-\u9fff]/;

function scoreText(value: string): number {
  let score = 0;

  if (cjkPattern.test(value)) {
    score += 3;
  }

  if (!suspiciousPattern.test(value)) {
    score += 2;
  }

  if (!value.includes("�")) {
    score += 1;
  }

  return score;
}

function decodeUtf8Mojibake(value: string): string {
  try {
    const bytes = Uint8Array.from(Array.from(value, (character) => character.charCodeAt(0) & 0xff));
    return new TextDecoder("utf-8", { fatal: false }).decode(bytes);
  } catch {
    return value;
  }
}

export function repairMojibakeString(value: string): string {
  if (!suspiciousPattern.test(value)) {
    return value;
  }

  const decoded = decodeUtf8Mojibake(value);
  return scoreText(decoded) > scoreText(value) ? decoded : value;
}

export function repairMojibakeValue<T>(value: T): T {
  if (typeof value === "string") {
    return repairMojibakeString(value) as T;
  }

  if (Array.isArray(value)) {
    return value.map((item) => repairMojibakeValue(item)) as T;
  }

  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => [key, repairMojibakeValue(item)])
    ) as T;
  }

  return value;
}

export function isLikelyMojibake(value: string | null | undefined): boolean {
  if (!value) {
    return false;
  }

  return suspiciousPattern.test(repairMojibakeString(value));
}

export function toSafeDisplayText(
  value: string | null | undefined,
  fallback: string,
  options?: { allowAscii?: boolean }
): string {
  const repaired = repairMojibakeString((value ?? "").trim());

  if (!repaired) {
    return fallback;
  }

  if (repaired === "未明确") {
    return fallback;
  }

  if (isLikelyMojibake(repaired)) {
    return fallback;
  }

  if (options?.allowAscii) {
    return repaired;
  }

  if (!cjkPattern.test(repaired) && /^[A-Za-z0-9 _./:+#-]+$/.test(repaired)) {
    return repaired;
  }

  return repaired;
}

export function toSafeDisplayList(values: string[] | null | undefined, fallback: string): string[] {
  const list = (values ?? [])
    .map((value) => toSafeDisplayText(value, ""))
    .filter(Boolean);

  return list.length > 0 ? list : [fallback];
}
