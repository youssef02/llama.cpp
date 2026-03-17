<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { Play, Save, WandSparkles, MessageSquareCode, X, ChevronDown, ChevronUp, PanelLeftClose, PanelLeftOpen, Container } from '@lucide/svelte';
	import { Button } from '$lib/components/ui/button';
	import { ideStore } from '$lib/stores/ide.svelte';
	import { goto } from '$app/navigation';
	import MonacoEditor from './MonacoEditor.svelte';
	import IdeFileTree from './IdeFileTree.svelte';
	import IdeTerminal from './IdeTerminal.svelte';
	import IdePodmanPanel from './IdePodmanPanel.svelte';

	let sidebarVisible = $state(true);
	let rightPanel = $state<'none'|'podman'>('none');
	let bottomH = $state(200);
	let sidebarW = $state(200);
	let cursorLine = $state(1); let cursorCol = $state(1);
	let editorRef: MonacoEditor;

	// resize state
	let resizingBottom = false, resizingSidebar = false;
	let startY = 0, startH = 0, startX = 0, startW = 0;

	onMount(async () => {
		await ideStore.checkPodmanApi();
		document.addEventListener('ide:cursor', (e) => { const {lineNumber,column} = (e as CustomEvent).detail; cursorLine=lineNumber; cursorCol=column; });
	});

	function startBottomResize(e: MouseEvent) { resizingBottom=true; startY=e.clientY; startH=bottomH; window.addEventListener('mousemove',onMove); window.addEventListener('mouseup',stopResize); }
	function startSidebarResize(e: MouseEvent) { resizingSidebar=true; startX=e.clientX; startW=sidebarW; window.addEventListener('mousemove',onMove); window.addEventListener('mouseup',stopResize); }
	function onMove(e: MouseEvent) {
		if (resizingBottom) bottomH = Math.max(80, Math.min(500, startH-(e.clientY-startY)));
		if (resizingSidebar) sidebarW = Math.max(140, Math.min(400, startW+(e.clientX-startX)));
	}
	function stopResize() { resizingBottom=resizingSidebar=false; window.removeEventListener('mousemove',onMove); window.removeEventListener('mouseup',stopResize); }

	function runInContainer() {
		const f = ideStore.activeFile; if (!f) return;
		const r = ideStore.containers.find((c) => c.status==='running');
		if (r) { ideStore.execInContainer(r.id, f.content, f.language); }
		else { ideStore.addTerminalLine('info','No running container — start one in the Containers panel.'); rightPanel='podman'; ideStore.bottomPanelOpen=true; }
	}

	function sendToChat() {
		const f = ideStore.activeFile; if (!f) return;
		goto(`/?new_chat=true&q=${encodeURIComponent(`Review this ${f.language} code from ${f.name}:\n\`\`\`${f.language}\n${f.content}\n\`\`\``)}`);
	}

	const LANG_LABEL: Record<string,string> = { python:'Python',javascript:'JavaScript',typescript:'TypeScript',dockerfile:'Dockerfile',bash:'Bash',json:'JSON',markdown:'Markdown',yaml:'YAML',rust:'Rust',go:'Go',plaintext:'Plain Text' };
</script>

<div class="flex h-full flex-col overflow-hidden bg-background">
	<!-- Toolbar -->
	<div class="flex flex-shrink-0 items-center gap-1.5 border-b border-border bg-background px-2 py-1.5">
		<Button variant="ghost" size="icon" class="h-7 w-7" onclick={() => (sidebarVisible=!sidebarVisible)} title="Toggle sidebar">
			{#if sidebarVisible}<PanelLeftClose class="h-4 w-4" />{:else}<PanelLeftOpen class="h-4 w-4" />{/if}
		</Button>
		<div class="mx-1 h-4 w-px bg-border"></div>
		<Button variant="ghost" size="sm" class="h-7 gap-1.5 text-xs text-green-500 hover:text-green-400" onclick={runInContainer}>
			<Play class="h-3.5 w-3.5" />Run
		</Button>
		<Button variant="ghost" size="sm" class="h-7 gap-1.5 text-xs" onclick={() => ideStore.activeFile && ideStore.saveFile(ideStore.activeFile.path)}>
			<Save class="h-3.5 w-3.5" />Save
		</Button>
		<Button variant="ghost" size="sm" class="h-7 gap-1.5 text-xs" onclick={() => editorRef?.formatDocument()}>
			<WandSparkles class="h-3.5 w-3.5" />Format
		</Button>
		<Button variant="ghost" size="sm" class="h-7 gap-1.5 text-xs" onclick={sendToChat}>
			<MessageSquareCode class="h-3.5 w-3.5" />Ask AI
		</Button>
		<div class="mx-1 h-4 w-px bg-border"></div>
		<Button variant="ghost" size="sm" class="h-7 gap-1.5 text-xs {rightPanel==='podman' ? 'text-primary' : ''}"
			onclick={() => (rightPanel=rightPanel==='podman'?'none':'podman')}>
			<Container class="h-3.5 w-3.5" />Containers
			{#if ideStore.containers.filter((c)=>c.status==='running').length > 0}
				<span class="flex h-4 min-w-4 items-center justify-center rounded-full bg-green-500/15 px-1 text-[10px] font-semibold text-green-500">
					{ideStore.containers.filter((c)=>c.status==='running').length}
				</span>
			{/if}
		</Button>
	</div>

	<!-- Tab bar -->
	<div class="flex flex-shrink-0 items-end overflow-x-auto border-b border-border bg-muted/30">
		{#each ideStore.openFiles as f (f.path)}
			<button class="group flex h-8 flex-shrink-0 items-center gap-2 border-r border-border px-3 text-xs transition-colors
				{ideStore.activeFilePath===f.path ? 'border-b-2 border-b-primary bg-background text-foreground' : 'text-muted-foreground hover:bg-background/60'}"
				onclick={() => ideStore.openFile(f.path)}>
				{#if f.isDirty}<span class="h-1.5 w-1.5 rounded-full bg-primary"></span>{/if}
				<span>{f.name}</span>
				<span class="ml-1 rounded p-0.5 opacity-0 hover:bg-muted group-hover:opacity-100" role="button" tabindex="0"
					onclick={(e) => { e.stopPropagation(); ideStore.closeFile(f.path); }}
					onkeydown={(e) => e.key==='Enter' && ideStore.closeFile(f.path)}>
					<X class="h-3 w-3" />
				</span>
			</button>
		{/each}
	</div>

	<!-- Work area -->
	<div class="flex min-h-0 flex-1 overflow-hidden">
		{#if sidebarVisible}
			<div class="flex-shrink-0 overflow-y-auto border-r border-border bg-sidebar" style="width:{sidebarW}px">
				<p class="px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Explorer</p>
				<IdeFileTree />
			</div>
			<div class="w-1 flex-shrink-0 cursor-col-resize hover:bg-primary/30" role="separator" aria-orientation="vertical" onmousedown={startSidebarResize}></div>
		{/if}

		<div class="flex min-w-0 flex-1 flex-col overflow-hidden">
			<div class="min-h-0 flex-1 overflow-hidden">
				{#if ideStore.activeFile}
					<MonacoEditor bind:this={editorRef} path={ideStore.activeFile.path} content={ideStore.activeFile.content} language={ideStore.activeFile.language} />
				{:else}
					<div class="flex h-full items-center justify-center text-center text-muted-foreground">
						<div><p class="text-sm">No file open</p><p class="mt-1 text-xs">Select a file from the explorer</p></div>
					</div>
				{/if}
			</div>

			{#if ideStore.bottomPanelOpen}
				<div class="h-1 flex-shrink-0 cursor-row-resize hover:bg-primary/30" role="separator" aria-orientation="horizontal" onmousedown={startBottomResize}></div>
				<div class="flex-shrink-0 overflow-hidden border-t border-border" style="height:{bottomH}px"><IdeTerminal /></div>
			{/if}

			<div class="flex flex-shrink-0 items-center justify-end border-t border-border bg-muted/10 px-2 py-0.5">
				<button class="flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground"
					onclick={() => (ideStore.bottomPanelOpen=!ideStore.bottomPanelOpen)}>
					{#if ideStore.bottomPanelOpen}<ChevronDown class="h-3 w-3" />{:else}<ChevronUp class="h-3 w-3" />{/if}
					Terminal
				</button>
			</div>
		</div>

		{#if rightPanel==='podman'}
			<div class="w-[320px] flex-shrink-0 overflow-hidden border-l border-border xl:w-[360px]"><IdePodmanPanel /></div>
		{/if}
	</div>

	<!-- Status bar -->
	<div class="flex flex-shrink-0 items-center gap-3 border-t border-border bg-primary px-3 py-0.5 text-[11px] font-medium text-primary-foreground">
		{#if ideStore.activeFile}
			<span>{ideStore.activeFile.name}</span>
			<span class="opacity-50">|</span>
			<span>{LANG_LABEL[ideStore.activeFile.language] ?? ideStore.activeFile.language}</span>
			<span class="opacity-50">|</span>
			<span>Ln {cursorLine}, Col {cursorCol}</span>
		{/if}
		<span class="ml-auto flex items-center gap-1.5">
			<span class="h-1.5 w-1.5 rounded-full {ideStore.containers.some((c)=>c.status==='running') ? 'bg-green-300' : 'bg-primary-foreground/30'}"></span>
			{ideStore.containers.filter((c)=>c.status==='running').length} running
		</span>
	</div>
</div>
