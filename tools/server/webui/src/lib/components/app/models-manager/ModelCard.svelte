<script lang="ts">
	import { Play, Square, RefreshCw, ChevronDown, ChevronUp, Copy } from '@lucide/svelte';
	import { Button } from '$lib/components/ui/button';
	import ModelStatusBadge from './ModelStatusBadge.svelte';
	import { modelsStore } from '$lib/stores/models.svelte';
	import { modelManagerStore } from '$lib/stores/model-manager.svelte';
	import { ServerModelStatus } from '$lib/enums';
	import type { ApiModelDataEntry } from '$lib/types/api';

	interface Props { model: ApiModelDataEntry; }
	let { model }: Props = $props();

	let expanded  = $state(false);
	let status    = $derived(model.status?.value as ServerModelStatus ?? ServerModelStatus.UNLOADED);
	let isLoaded  = $derived(status === ServerModelStatus.LOADED);
	let isLoading = $derived(status === ServerModelStatus.LOADING || modelsStore.isModelOperationInProgress(model.id));
	let isFailed  = $derived(status === ServerModelStatus.FAILED);
	let ctxSize   = $derived(modelsStore.getModelContextSize(model.id));
	let args      = $derived((model.status as any)?.args as string[] | undefined);

	function displayName(id: string) { return id.split(/[/\\]/).pop() ?? id; }
	function copyId() { navigator.clipboard.writeText(model.id).catch(() => {}); }
</script>

<div class="rounded-lg border bg-card transition-colors
	{isLoaded ? 'border-green-500/30' : isFailed ? 'border-destructive/30' : 'border-border'}">
	<div class="flex items-start gap-3 p-3">
		<span class="mt-1.5 h-2 w-2 flex-shrink-0 rounded-full
			{isLoaded ? 'bg-green-400 shadow-[0_0_6px] shadow-green-400/60' : ''}
			{isLoading ? 'animate-pulse bg-yellow-400' : ''}
			{isFailed ? 'bg-destructive' : ''}
			{!isLoaded && !isLoading && !isFailed ? 'bg-muted-foreground/25' : ''}">
		</span>
		<div class="min-w-0 flex-1">
			<div class="flex flex-wrap items-center gap-2">
				<span class="truncate text-sm font-semibold" title={model.id}>{displayName(model.id)}</span>
				<ModelStatusBadge {status} />
				{#each (model.tags ?? []) as tag}
					<span class="rounded-full bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">{tag}</span>
				{/each}
			</div>
			<button class="mt-0.5 flex items-center gap-1 font-mono text-[11px] text-muted-foreground hover:text-foreground" onclick={copyId}>
				<span class="max-w-[280px] truncate">{model.id}</span>
				<Copy class="h-2.5 w-2.5 flex-shrink-0" />
			</button>
			{#if (model.aliases ?? []).length > 0}
				<p class="mt-0.5 text-[11px] text-muted-foreground">aliases: {(model.aliases ?? []).join(', ')}</p>
			{/if}
		</div>
		<div class="flex flex-shrink-0 items-center gap-1.5">
			{#if isLoading}
				<Button variant="ghost" size="sm" class="h-7 gap-1.5 text-xs" disabled>
					<RefreshCw class="h-3.5 w-3.5 animate-spin" />Working…
				</Button>
			{:else if isLoaded}
				<Button variant="outline" size="sm" class="h-7 gap-1.5 text-xs text-destructive hover:bg-destructive/10 hover:text-destructive"
					onclick={() => modelManagerStore.unloadModel(model.id)}>
					<Square class="h-3 w-3" />Unload
				</Button>
			{:else}
				<Button variant="outline" size="sm" class="h-7 gap-1.5 text-xs"
					onclick={() => modelManagerStore.loadModel(model.id)} disabled={isFailed}>
					<Play class="h-3 w-3" />Load
				</Button>
			{/if}
			<Button variant="ghost" size="icon" class="h-7 w-7" onclick={() => (expanded = !expanded)}>
				{#if expanded}<ChevronUp class="h-3.5 w-3.5" />{:else}<ChevronDown class="h-3.5 w-3.5" />{/if}
			</Button>
		</div>
	</div>
	{#if expanded}
		<div class="space-y-2 border-t border-border px-4 py-3 text-xs">
			{#if isLoaded && ctxSize}
				<p class="text-muted-foreground">Context: {ctxSize.toLocaleString()} tokens</p>
			{/if}
			{#if isFailed}
				<div class="rounded bg-destructive/10 px-2 py-1.5 text-destructive">
					Failed to load.{(model.status as any)?.exit_code !== undefined ? ` Exit code: ${(model.status as any).exit_code}.` : ''} Check llama-server logs.
				</div>
			{/if}
			{#if args && args.length > 0}
				<div><p class="mb-1 font-medium text-muted-foreground">Launch args</p>
					<pre class="overflow-x-auto rounded bg-muted/50 p-2 text-[11px] leading-5">{args.join(' ')}</pre>
				</div>
			{/if}
			{#if (model.status as any)?.preset}
				<div><p class="mb-1 font-medium text-muted-foreground">Preset</p>
					<pre class="overflow-x-auto rounded bg-muted/50 p-2 text-[11px] leading-5">{(model.status as any).preset}</pre>
				</div>
			{/if}
		</div>
	{/if}
</div>
