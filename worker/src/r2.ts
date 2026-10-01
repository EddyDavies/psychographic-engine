import type { Env } from './index';

export interface ManifestEntry {
  copy_file: string;
  image_files: Record<string, string>;  // ratio → filename
  review_status: string;
  angle_name: string;
  sub_avatar: string;
  visual_format: string;
  messaging_concept: string;
  primary_text: string;
  headline: string;
  sequence: number;
  ad_set_key: string;
  [key: string]: unknown;
}

/** List batch names from R2 (objects under batches/ prefix) */
export async function listBatches(env: Env): Promise<string[]> {
  const prefixes: string[] = [];
  let cursor: string | undefined;
  do {
    const listed = await env.R2.list({ prefix: 'batches/', delimiter: '/', cursor });
    for (const p of listed.delimitedPrefixes ?? []) {
      prefixes.push(p.replace('batches/', '').replace('/', ''));
    }
    cursor = listed.truncated ? listed.cursor : undefined;
  } while (cursor);
  return prefixes.sort();
}

/** Download manifest.json for a batch. Returns null if not found. */
export async function getBatchManifest(
  env: Env,
  batchName: string
): Promise<ManifestEntry[] | null> {
  const obj = await env.R2.get(`batches/${batchName}/manifest.json`);
  if (!obj) return null;
  return (await obj.json()) as ManifestEntry[];
}

/** Get a public URL for an R2 object via the Worker image proxy route */
export function imageProxyUrl(request: Request, batchName: string, filename: string): string {
  const base = new URL(request.url).origin;
  return `${base}/api/images/${encodeURIComponent(batchName)}/${encodeURIComponent(filename)}`;
}

/** Get a raw R2 object — returns null if not found */
export async function getObject(env: Env, key: string): Promise<R2ObjectBody | null> {
  return env.R2.get(key);
}
