<script lang="ts">
	import { Play, Square, Trash2, Terminal, Plus, Rocket, ScrollText } from '@lucide/svelte';
	import { Button } from '$lib/components/ui/button';
	import { ideStore, type PodmanContainer } from '$lib/stores/ide.svelte';

	let showForm = $state(false);
	let newName = $state(''); let newImage = $state('python:3.12-slim');
	let newPort = $state(''); let newMount = $state('');
	let newEnv = $state(''); let newCmd = $state('');

	const IMAGES = ['python:3.12-slim','python:3.11-slim','node:20-alpine','node:18-alpine','ubuntu:22.04','alpine:3.19','rust:1.76-slim','golang:1.22-alpine'];

	function fmt(s?: number) { if (!s) return '–'; if (s<60) return `${s}s`; if (s<3600) return `${Math.floor(s/60)}m`; return `${Math.floor(s/3600)}h`; }

	async function handleCreate() {
		if (!newName.trim() || !newImage.trim()) return;
		await ideStore.createContainer({ name:newName.trim(), image:newImage.trim(), ports:newPort, mountPath:newMount, env:newEnv, cmd:newCmd });
		newName=''; newPort=''; newMount=''; newEnv=''; newCmd=''; showForm=false;
	}
</script>
<div class="h-full overflow-y-auto p-4">
	<div class="mb-4 flex items-center justify-between">
		<div>
			<h2 class="text-sm font-semibold">Containers</h2>
			<p class="text-xs text-muted-foreground">
				{ideStore.podmanAvailable ? 'Podman connected' : 'Start sidecar to use Podman'}
			</p>
		</div>
		<Button variant="outline" size="sm" onclick={() => (showForm=!showForm)}><Plus class="mr-1.5 h-3.5 w-3.5" />New</Button>
	</div>

	<div class="mb-4 space-y-2">
		{#each ideStore.containers as c (c.id)}
			<div class="rounded-lg border bg-card p-3 {c.status==='running' ? 'border-green-500/30' : 'border-border'}">
				<div class="mb-1.5 flex items-center justify-between">
					<div class="flex items-center gap-2">
						<span class="h-2 w-2 rounded-full {c.status==='running' ? 'bg-green-400 shadow-[0_0_5px] shadow-green-400/60' : c.status==='building' ? 'animate-pulse bg-yellow-400' : 'bg-muted-foreground/30'}"></span>
						<span class="text-sm font-medium">{c.name}</span>
					</div>
					<span class="rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase
						{c.status==='running' ? 'bg-green-500/10 text-green-500' : c.status==='building' ? 'bg-yellow-500/10 text-yellow-500' : 'bg-muted text-muted-foreground'}">
						{c.status}
					</span>
				</div>
				<p class="mb-2 font-mono text-[11px] text-muted-foreground">{c.image}</p>
				{#if c.status==='running'}
					<p class="mb-2 text-[11px] text-muted-foreground">{(c.cpuPercent??0).toFixed(1)}% CPU · {c.memoryMB??0} MB · {fmt(c.uptimeSeconds)}</p>
				{/if}
				<div class="flex flex-wrap gap-1.5">
					{#if c.status==='running'}
						<Button variant="outline" size="sm" class="h-7 text-xs"
							onclick={() => { const f=ideStore.activeFile; if(f) ideStore.execInContainer(c.id,f.content,f.language); }}>
							<Play class="mr-1 h-3 w-3" />Run file
						</Button>
						<Button variant="outline" size="sm" class="h-7 text-xs"
							onclick={() => { ideStore.addTerminalLine('info',`Opening terminal in ${c.name}…`); ideStore.activeBottomPanel='terminal'; }}>
							<Terminal class="mr-1 h-3 w-3" />Terminal
						</Button>
						<Button variant="outline" size="sm" class="h-7 text-xs" onclick={() => ideStore.stopContainer(c.id)}>
							<Square class="mr-1 h-3 w-3" />Stop
						</Button>
					{:else if c.status==='stopped'}
						<Button variant="outline" size="sm" class="h-7 text-xs" onclick={() => ideStore.startContainer(c.id)}>
							<Play class="mr-1 h-3 w-3" />Start
						</Button>
						<Button variant="ghost" size="sm" class="h-7 text-xs text-destructive hover:text-destructive" onclick={() => ideStore.removeContainer(c.id)}>
							<Trash2 class="mr-1 h-3 w-3" />Remove
						</Button>
					{:else}
						<Button variant="ghost" size="sm" class="h-7 text-xs" disabled><span class="animate-pulse">Building…</span></Button>
					{/if}
					<Button variant="ghost" size="sm" class="h-7 text-xs text-muted-foreground"
						onclick={() => ideStore.addTerminalLine('info',`Logs from ${c.name}…`)}>
						<ScrollText class="mr-1 h-3 w-3" />Logs
					</Button>
				</div>
			</div>
		{/each}
		{#if ideStore.containers.length === 0 && !showForm}
			<button class="flex w-full flex-col items-center gap-2 rounded-lg border border-dashed border-border py-8 text-muted-foreground hover:border-primary/40 hover:text-primary"
				onclick={() => (showForm=true)}>
				<Plus class="h-5 w-5" /><span class="text-xs">New container</span>
			</button>
		{/if}
	</div>

	{#if showForm}
		<div class="rounded-lg border border-border bg-card p-4">
			<h3 class="mb-3 text-sm font-semibold">New container</h3>
			<div class="space-y-2.5">
				<div class="grid grid-cols-2 gap-2">
					<div><label class="mb-1 block text-[11px] text-muted-foreground">Name</label>
						<input class="h-8 w-full rounded-md border border-input bg-background px-2.5 text-xs outline-none focus:ring-1 focus:ring-ring" placeholder="my-sandbox" bind:value={newName} /></div>
					<div><label class="mb-1 block text-[11px] text-muted-foreground">Image</label>
						<select class="h-8 w-full rounded-md border border-input bg-background px-2.5 text-xs outline-none focus:ring-1 focus:ring-ring" bind:value={newImage}>
							{#each IMAGES as img}<option value={img}>{img}</option>{/each}
						</select></div>
				</div>
				<div class="grid grid-cols-2 gap-2">
					<div><label class="mb-1 block text-[11px] text-muted-foreground">Mount path</label>
						<input class="h-8 w-full rounded-md border border-input bg-background px-2.5 font-mono text-xs outline-none focus:ring-1 focus:ring-ring" placeholder="/home/user/project" bind:value={newMount} /></div>
					<div><label class="mb-1 block text-[11px] text-muted-foreground">Port</label>
						<input class="h-8 w-full rounded-md border border-input bg-background px-2.5 font-mono text-xs outline-none focus:ring-1 focus:ring-ring" placeholder="8080:8080" bind:value={newPort} /></div>
				</div>
				<div><label class="mb-1 block text-[11px] text-muted-foreground">Env vars (KEY=val per line)</label>
					<textarea class="w-full rounded-md border border-input bg-background px-2.5 py-1.5 font-mono text-xs outline-none focus:ring-1 focus:ring-ring" rows="2" bind:value={newEnv}></textarea></div>
				<div class="flex gap-2">
					<Button class="h-8 text-xs" onclick={handleCreate} disabled={!newName||!newImage}>
						<Rocket class="mr-1.5 h-3.5 w-3.5" />Launch
					</Button>
					<Button variant="outline" class="h-8 text-xs" onclick={() => (showForm=false)}>Cancel</Button>
				</div>
			</div>
		</div>
	{/if}

	{#if !ideStore.podmanAvailable}
		<div class="mt-4 rounded-lg border border-border bg-muted/20 p-3 text-xs text-muted-foreground">
			<p class="font-medium text-foreground">Connect the IDE sidecar</p>
			<pre class="mt-2 overflow-x-auto rounded bg-background p-2 text-[11px]">pip install fastapi uvicorn docker
python tools/server/ide-sidecar/main.py</pre>
			<p class="mt-1">Then enable Podman: <code>systemctl --user enable --now podman.socket</code></p>
		</div>
	{/if}
</div>
