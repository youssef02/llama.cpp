<script lang="ts">
	import { Trash2 } from '@lucide/svelte';
	import { ideStore } from '$lib/stores/ide.svelte';
	import { tick } from 'svelte';
	let scrollEl: HTMLDivElement;
	$effect(() => { ideStore.terminalLines; tick().then(() => scrollEl && (scrollEl.scrollTop = scrollEl.scrollHeight)); });
	function onKeydown(e: KeyboardEvent) {
		if (e.key !== 'Enter') return;
		const cmd = ideStore.terminalInput.trim(); if (!cmd) return;
		ideStore.addTerminalLine('command', `$ ${cmd}`);
		ideStore.addTerminalLine('info', '(shell exec requires the IDE sidecar)');
		ideStore.terminalInput = '';
	}
</script>
<div class="flex h-full flex-col font-mono text-xs">
	<div class="flex flex-shrink-0 items-center justify-between border-b border-border px-3 py-1">
		<div class="flex gap-0.5">
			{#each (['terminal','output','problems'] as const) as t}
				<button class="rounded px-2.5 py-1 text-xs transition-colors {ideStore.activeBottomPanel===t ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:text-foreground'}"
					onclick={() => (ideStore.activeBottomPanel = t)}>{t[0].toUpperCase()+t.slice(1)}</button>
			{/each}
		</div>
		<button class="text-muted-foreground hover:text-foreground" onclick={() => ideStore.clearTerminal()} title="Clear"><Trash2 class="h-3.5 w-3.5" /></button>
	</div>
	<div bind:this={scrollEl} class="flex-1 overflow-y-auto px-3 py-2 space-y-0.5">
		{#each ideStore.terminalLines as line (line.id)}
			<div class="flex gap-2 leading-5">
				{#if line.type==='command'}
					<span class="flex-shrink-0 text-green-400">$</span><span>{line.text.replace(/^\$\s*/,'')}</span>
				{:else if line.type==='stderr'}
					<span class="flex-shrink-0 text-muted-foreground"> </span><span class="text-red-400">{line.text}</span>
				{:else if line.type==='success'}
					<span class="flex-shrink-0 text-muted-foreground"> </span><span class="text-green-400">{line.text}</span>
				{:else if line.type==='info'}
					<span class="flex-shrink-0 text-muted-foreground">#</span><span class="text-muted-foreground">{line.text}</span>
				{:else}
					<span class="flex-shrink-0 text-muted-foreground"> </span><span>{line.text}</span>
				{/if}
			</div>
		{/each}
	</div>
	<div class="flex items-center gap-2 border-t border-border px-3 py-1.5">
		<span class="flex-shrink-0 text-green-400">$</span>
		<input class="flex-1 bg-transparent text-xs outline-none placeholder:text-muted-foreground"
			placeholder="enter command…" bind:value={ideStore.terminalInput} onkeydown={onKeydown} />
	</div>
</div>
