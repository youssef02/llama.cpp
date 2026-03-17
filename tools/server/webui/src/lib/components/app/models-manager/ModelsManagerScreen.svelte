<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { RefreshCw, Server, HardDrive, Loader2, AlertCircle } from '@lucide/svelte';
	import { Button } from '$lib/components/ui/button';
	import { modelsStore, routerModels } from '$lib/stores/models.svelte';
	import { serverStore } from '$lib/stores/server.svelte';
	import { modelManagerStore } from '$lib/stores/model-manager.svelte';
	import { ServerModelStatus } from '$lib/enums';
	import ModelCard from './ModelCard.svelte';
	import GgufScanner from './GgufScanner.svelte';

	type Tab = 'router' | 'scan';
	let tab = $state<Tab>('router');
	let refreshing = $state(false);
	let search = $state('');
	let filterStatus = $state<'all' | ServerModelStatus>('all');

	let all     = $derived(routerModels());
	let loaded  = $derived(all.filter((m) => m.status?.value === ServerModelStatus.LOADED).length);
	let loading = $derived(all.filter((m) => m.status?.value === ServerModelStatus.LOADING).length);
	let failed  = $derived(all.filter((m) => (m.status as any)?.failed).length);

	let filtered = $derived.by(() => {
		let list = all;
		if (filterStatus !== 'all') list = list.filter((m) => m.status?.value === filterStatus);
		if (search.trim()) {
			const q = search.toLowerCase();
			list = list.filter((m) => m.id.toLowerCase().includes(q) || (m.aliases ?? []).some((a) => a.toLowerCase().includes(q)));
		}
		return list;
	});

	async function refresh() {
		if (refreshing) return;
		refreshing = true;
		try { await modelsStore.fetchRouterModels(); await modelManagerStore.probeSidecar(); }
		finally { refreshing = false; }
	}

	onMount(async () => {
		if (modelsStore.models.length === 0) await modelsStore.fetch();
		if (serverStore.isRouterMode) await modelsStore.fetchRouterModels();
		await modelManagerStore.probeSidecar();
		modelManagerStore.startPolling(5);
	});
	onDestroy(() => modelManagerStore.stopPolling());
</script>

<div class="flex h-full flex-col overflow-hidden">
	<div class="flex flex-shrink-0 items-center justify-between border-b border-border px-6 py-4">
		<div>
			<h1 class="text-base font-semibold">Model Manager</h1>
			<p class="text-xs text-muted-foreground">
				{#if serverStore.isRouterMode}
					Router mode · {all.length} registered
				{:else}
					Single-model mode · start with <code class="rounded bg-muted px-1">--router</code> for dynamic loading
				{/if}
			</p>
		</div>
		<Button variant="outline" size="sm" class="h-8 gap-1.5 text-xs" onclick={refresh} disabled={refreshing}>
			<RefreshCw class="h-3.5 w-3.5 {refreshing ? 'animate-spin' : ''}" />Refresh
		</Button>
	</div>

	{#if serverStore.isRouterMode}
		<div class="flex flex-shrink-0 items-center gap-3 border-b border-border bg-muted/20 px-6 py-1.5 text-xs">
			<button class="{filterStatus === 'all' ? 'font-semibold text-foreground' : 'text-muted-foreground'}" onclick={() => (filterStatus = 'all')}>
				All <span class="ml-1 rounded-full bg-muted px-1.5 py-0.5 text-[10px]">{all.length}</span>
			</button>
			<button class="flex items-center gap-1 {filterStatus === ServerModelStatus.LOADED ? 'font-semibold text-green-500' : 'text-muted-foreground'}"
				onclick={() => (filterStatus = filterStatus === ServerModelStatus.LOADED ? 'all' : ServerModelStatus.LOADED)}>
				<span class="h-1.5 w-1.5 rounded-full bg-green-400"></span>
				Loaded <span class="ml-1 rounded-full bg-green-500/10 px-1.5 py-0.5 text-[10px] text-green-500">{loaded}</span>
			</button>
			{#if loading > 0}
				<span class="flex items-center gap-1 text-yellow-500">
					<Loader2 class="h-3 w-3 animate-spin" />Loading {loading}
				</span>
			{/if}
			{#if failed > 0}
				<button class="flex items-center gap-1 text-destructive" onclick={() => (filterStatus = ServerModelStatus.FAILED)}>
					<AlertCircle class="h-3 w-3" />Failed {failed}
				</button>
			{/if}
			<span class="ml-auto flex items-center gap-1.5 text-muted-foreground">
				<span class="h-1.5 w-1.5 rounded-full {modelManagerStore.sidecarAvailable ? 'bg-green-400' : 'bg-muted-foreground/30'}"></span>
				sidecar {modelManagerStore.sidecarAvailable ? 'connected' : 'offline'}
			</span>
		</div>
	{/if}

	<div class="flex flex-shrink-0 gap-0.5 border-b border-border px-4">
		{#each ([['router', Server, 'Registered models'], ['scan', HardDrive, 'Scan GGUF files']] as const) as [id, Icon, label]}
			<button class="flex items-center gap-1.5 border-b-2 px-3 py-2 text-xs transition-colors
				{tab === id ? 'border-primary font-medium text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground'}"
				onclick={() => (tab = id)}>
				<Icon class="h-3.5 w-3.5" />{label}
			</button>
		{/each}
	</div>

	<div class="min-h-0 flex-1 overflow-y-auto p-4">
		{#if tab === 'router'}
			{#if !serverStore.isRouterMode}
				<div class="flex flex-col items-center gap-3 py-16 text-center">
					<Server class="h-10 w-10 text-muted-foreground/30" />
					<div>
						<p class="text-sm font-medium">Router mode not enabled</p>
						<p class="mt-1 text-xs text-muted-foreground">Start llama-server with <code class="rounded bg-muted px-1">--router --models-dir /path/to/models</code></p>
					</div>
				</div>
			{:else if modelsStore.loading}
				<div class="flex items-center justify-center py-16"><Loader2 class="h-6 w-6 animate-spin text-muted-foreground" /></div>
			{:else if all.length === 0}
				<div class="flex flex-col items-center gap-3 py-16 text-center text-muted-foreground">
					<Server class="h-10 w-10 opacity-30" />
					<p class="text-sm font-medium">No models registered</p>
					<p class="text-xs">Use the <button class="text-primary hover:underline" onclick={() => (tab = 'scan')}>GGUF scanner</button> or add models to your config.</p>
				</div>
			{:else}
				<input class="mb-3 h-8 w-full rounded-md border border-input bg-background px-3 text-xs outline-none placeholder:text-muted-foreground focus:ring-1 focus:ring-ring"
					placeholder="Filter by name, alias, or tag…" bind:value={search} />
				{#if filtered.length === 0}
					<p class="py-8 text-center text-xs text-muted-foreground">No models match that filter.</p>
				{:else}
					<div class="space-y-2">
						{#each filtered as model (model.id)}<ModelCard {model} />{/each}
					</div>
				{/if}
			{/if}
		{:else}
			<GgufScanner />
		{/if}
	</div>
</div>
