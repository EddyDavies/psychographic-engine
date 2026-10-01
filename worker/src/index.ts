import { listBatches, getBatchManifest, getObject, imageProxyUrl } from './r2';

export interface Env {
  R2: R2Bucket;
  ASSETS: Fetcher;
}

function json(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

async function handleListBatches(env: Env): Promise<Response> {
  const batches = await listBatches(env);
  return json({ batches });
}

async function handleGetBatch(request: Request, env: Env, name: string): Promise<Response> {
  const entries = await getBatchManifest(env, name);
  if (!entries) return json({ error: 'Batch not found' }, 404);

  const enriched = entries.map(entry => ({
    ...entry,
    image_urls: Object.fromEntries(
      Object.entries(entry.image_files ?? {}).map(([ratio, filename]) => [
        ratio,
        imageProxyUrl(request, name, filename as string),
      ])
    ),
  }));

  return json({ entries: enriched });
}

async function handleProxyImage(env: Env, batchName: string, filename: string): Promise<Response> {
  const key = `batches/${batchName}/${filename}`;
  const obj = await getObject(env, key);
  if (!obj) return new Response('Not found', { status: 404 });

  return new Response(obj.body, {
    headers: {
      'Content-Type': obj.httpMetadata?.contentType ?? 'image/png',
      'Cache-Control': 'public, max-age=3600',
      'ETag': obj.httpEtag,
    },
  });
}

async function handleApprove(_request: Request, _env: Env, name: string): Promise<Response> {
  return json(
    { message: 'Approval is handled via CLI', batchName: name },
    501,
  );
}

async function handleGenerate(): Promise<Response> {
  return json(
    { detail: 'Generation runs via CLI: cd scripts && uv run python generate-ads.py --client <client> --count <n> [--sub-avatar <avatar>...] [--messaging <concept> [<concept>...]] --upload-r2' },
    501,
  );
}

async function handleGetJob(_jobId: string): Promise<Response> {
  return json(
    { detail: 'Job polling is not implemented. Run generation via CLI.' },
    501,
  );
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const pathname = url.pathname;
    const method = request.method;

    if (method === 'GET' && pathname === '/api/batches') {
      return handleListBatches(env);
    }

    if (method === 'GET' && pathname.startsWith('/api/batches/') && !pathname.includes('/approve')) {
      const name = decodeURIComponent(pathname.replace('/api/batches/', ''));
      return handleGetBatch(request, env, name);
    }

    if (method === 'GET' && pathname.startsWith('/api/images/')) {
      const parts = pathname.replace('/api/images/', '').split('/');
      return handleProxyImage(env, decodeURIComponent(parts[0]), decodeURIComponent(parts[1]));
    }

    if (method === 'POST' && pathname.startsWith('/api/batches/') && pathname.endsWith('/approve')) {
      const name = decodeURIComponent(pathname.replace('/api/batches/', '').replace('/approve', ''));
      return handleApprove(request, env, name);
    }

    if (method === 'POST' && pathname === '/api/generate') {
      return handleGenerate();
    }

    if (method === 'GET' && pathname.startsWith('/api/jobs/')) {
      const jobId = decodeURIComponent(pathname.replace('/api/jobs/', ''));
      return handleGetJob(jobId);
    }

    return env.ASSETS.fetch(request);
  },
};
