/**
 * modelManagerStore
 * Extends modelsStore with:
 *  - GGUF file discovery via sidecar /ide/gguf/scan
 *  - load/unload delegating to real modelsStore (POST /models/load, /models/unload)
 *  - live polling of router model status
 */
import { modelsStore } from '$lib/stores/models.svelte';
import { serverStore } from '$lib/stores/server.svelte';
import { browser } from '$app/environment';

export interface GgufFile {
	path: string;
	name: string;
	sizeMB: number;
	modifiedAt: string;
	isRegistered: boolean;
	modelId?: string;
}

function createModelManagerStore() {
	let ggufFiles     = $state<GgufFile[]>([]);
	let ggufScanDir   = $state('');
	let ggufScanning  = $state(false);
	let ggufScanError = $state<string | null>(null);
	let sidecarAvailable = $state(false);
	let pollTimer: ReturnType<typeof setInterval> | null = null;

	async function probeSidecar(): Promise<boolean> {
		if (!browser) return false;
		try {
			const r = await fetch('/ide/health', { signal: AbortSignal.timeout(1500) });
			if (r.ok) {
				const data = await r.json();
				sidecarAvailable = true;
				// Use the absolute path reported by the sidecar so the scanner
				// works regardless of what directory the sidecar was started from.
				// Falls back to the relative 'models' string (works for dev proxy).
				if (!ggufScanDir && data.default_models_dir) {
					ggufScanDir = data.default_models_dir;
				} else if (!ggufScanDir) {
					ggufScanDir = 'models';
				}
			} else {
				sidecarAvailable = false;
			}
		} catch { sidecarAvailable = false; }
		return sidecarAvailable;
	}

	async function scanGgufDir(dir?: string): Promise<void> {
		if (!browser) return;
		await probeSidecar();
		if (!sidecarAvailable) {
			ggufScanError = 'IDE sidecar not running — see tools/server/ide-sidecar/README.md';
			return;
		}
		const scanPath = dir ?? ggufScanDir;
		if (!scanPath.trim()) { ggufScanError = 'Enter a directory path first'; return; }
		ggufScanning = true; ggufScanError = null;
		try {
			const url = new URL('/ide/gguf/scan', window.location.href);
			url.searchParams.set('dir', scanPath);
			const res = await fetch(url.toString());
			if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail ?? `HTTP ${res.status}`);
			const data: { files: Array<{ path: string; name: string; size_bytes: number; modified_at: string }> } = await res.json();
			const registeredPaths = new Set(modelsStore.routerModels.map((m) => (m as any).path as string).filter(Boolean));
			ggufFiles = data.files.map((f) => ({
				path: f.path, name: f.name,
				sizeMB: Math.round(f.size_bytes / (1024 * 1024)),
				modifiedAt: f.modified_at,
				isRegistered: registeredPaths.has(f.path),
				modelId: modelsStore.routerModels.find((m) => (m as any).path === f.path)?.id
			}));
			ggufScanDir = scanPath;
		} catch (e) {
			ggufScanError = e instanceof Error ? e.message : String(e);
		} finally { ggufScanning = false; }
	}

	async function loadModel(modelId: string) {
		await modelsStore.loadModel(modelId);
		if (ggufFiles.length > 0) await scanGgufDir();
	}

	async function unloadModel(modelId: string) {
		await modelsStore.unloadModel(modelId);
		if (ggufFiles.length > 0) await scanGgufDir();
	}

	function startPolling(intervalSecs = 5) {
		stopPolling();
		if (!serverStore.isRouterMode) return;
		pollTimer = setInterval(async () => {
			try { await modelsStore.fetchRouterModels(); } catch { /* ignore */ }
		}, intervalSecs * 1000);
	}

	function stopPolling() {
		if (pollTimer !== null) { clearInterval(pollTimer); pollTimer = null; }
	}

	return {
		get ggufFiles() { return ggufFiles; },
		get ggufScanDir() { return ggufScanDir; },
		set ggufScanDir(v: string) { ggufScanDir = v; },
		get ggufScanning() { return ggufScanning; },
		get ggufScanError() { return ggufScanError; },
		get sidecarAvailable() { return sidecarAvailable; },
		probeSidecar, scanGgufDir, loadModel, unloadModel, startPolling, stopPolling,
	};
}

export const modelManagerStore = createModelManagerStore();
