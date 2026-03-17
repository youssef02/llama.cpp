<script lang="ts">
	import { FolderSearch, RefreshCw, HardDrive, Play, AlertCircle, Info } from '@lucide/svelte';
	import { Button } from '$lib/components/ui/button';
	import { modelManagerStore } from '$lib/stores/model-manager.svelte';
	import { routerModels } from '$lib/stores/models.svelte';
	import { ServerModelStatus } from '$lib/enums';
	import ModelStatusBadge from './ModelStatusBadge.svelte';
	import { onMount } from 'svelte';

	// Pre-fill with the server's default models directory and auto-scan if sidecar is available
	onMount(async () => {
		if (!modelManagerStore.ggufScanDir) {
			modelManagerStore.ggufScanDir = 'models';
		}
		// Auto-scan on first open if sidecar is already connected
		if (modelManagerStore.sidecarAvailable && modelManagerStore.ggufFiles.length === 0) {
			await modelManagerStore.scanGgufDir();
		}
	});

	function fmt(mb: number) { return mb >= 1024 ? `${(mb/1024).toFixed(1)} GB` : `${mb} MB`; }
	function modelIdFor(path: string) { return routerModels().find((m) => (m as any).path === path)?.id; }
	function statusFor(path: string) {
		const id = modelIdFor(path); if (!id) return undefined;
		return routerModels().find((m) => m.id === id)?.status?.value;
	}
	async function loadFile(path: string) {
		const id = modelIdFor(path); if (id) await modelManagerStore.loadModel(id);
	}
</script>

<div class="space-y-4">
	<div class="flex gap-2">
		<input class="h-9 flex-1 rounded-md border border-input bg-background px-3 font-mono text-xs outline-none placeholder:text-muted-foreground focus:ring-1 focus:ring-ring"
			placeholder="/home/user/models  or  C:\models"
			bind:value={modelManagerStore.ggufScanDir}
			onkeydown={(e) => e.key === 'Enter' && modelManagerStore.scanGgufDir()} />
		<Button variant="outline" size="sm" class="h-9 gap-1.5 whitespace-nowrap"
			onclick={() => modelManagerStore.scanGgufDir()} disabled={modelManagerStore.ggufScanning}>
			{#if modelManagerStore.ggufScanning}
				<RefreshCw class="h-3.5 w-3.5 animate-spin" />Scanning…
			{:else}
				<FolderSearch class="h-3.5 w-3.5" />Scan directory
			{/if}
		</Button>
	</div>

	<p class="text-[11px] text-muted-foreground flex items-center gap-1.5">
		<Info class="h-3 w-3 flex-shrink-0" />
		The server automatically scans <code class="rounded bg-muted px-1">./models</code> on startup (router mode).
		Drop .gguf files there or enter any path below.
	</p>

	{#if modelManagerStore.ggufScanError}
		<div class="flex items-start gap-2 rounded-lg border border-border bg-muted/30 p-3 text-xs">
			<AlertCircle class="mt-0.5 h-4 w-4 flex-shrink-0 text-yellow-500" />
			<div>
				<p class="font-medium text-foreground">{modelManagerStore.sidecarAvailable ? 'Scan error' : 'IDE sidecar not running'}</p>
				<p class="mt-0.5 text-muted-foreground">{modelManagerStore.ggufScanError}</p>
				{#if !modelManagerStore.sidecarAvailable}
					<pre class="mt-2 rounded bg-background px-2 py-1.5 text-[11px]">pip install fastapi uvicorn docker
python tools/server/ide-sidecar/main.py</pre>
				{/if}
			</div>
		</div>
	{/if}

	{#if modelManagerStore.ggufFiles.length > 0}
		<div class="space-y-1.5">
			<p class="text-xs text-muted-foreground">
				{modelManagerStore.ggufFiles.length} file{modelManagerStore.ggufFiles.length !== 1 ? 's' : ''} in
				<code class="rounded bg-muted px-1">{modelManagerStore.ggufScanDir}</code>
			</p>
			{#each modelManagerStore.ggufFiles as file (file.path)}
				{@const fs = statusFor(file.path)}
				{@const fid = modelIdFor(file.path)}
				<div class="flex items-center gap-3 rounded-md border border-border bg-card px-3 py-2 text-xs">
					<HardDrive class="h-4 w-4 flex-shrink-0 text-muted-foreground" />
					<div class="min-w-0 flex-1">
						<p class="truncate font-medium">{file.name}</p>
						<p class="truncate font-mono text-[11px] text-muted-foreground">{file.path}</p>
						<p class="text-[11px] text-muted-foreground">{fmt(file.sizeMB)} · {new Date(file.modifiedAt).toLocaleDateString()}</p>
					</div>
					{#if fs}<ModelStatusBadge status={fs} />{/if}
					{#if fid}
						{#if !fs || fs === ServerModelStatus.UNLOADED}
							<Button variant="outline" size="sm" class="h-7 gap-1 text-xs" onclick={() => loadFile(file.path)}>
								<Play class="h-3 w-3" />Load
							</Button>
						{/if}
					{:else}
						<span class="rounded-full bg-muted px-2 py-0.5 text-[10px] text-muted-foreground">not registered</span>
					{/if}
				</div>
			{/each}
		</div>
	{:else if !modelManagerStore.ggufScanning && modelManagerStore.ggufScanDir && modelManagerStore.sidecarAvailable && !modelManagerStore.ggufScanError}
		<p class="py-6 text-center text-xs text-muted-foreground">No .gguf files found in that directory.</p>
	{/if}
</div>
