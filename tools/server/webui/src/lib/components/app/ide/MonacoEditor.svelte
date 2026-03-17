<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { ideStore } from '$lib/stores/ide.svelte';

	interface Props { path: string; content: string; language: string; }
	let { path, content, language }: Props = $props();

	let container: HTMLDivElement;
	let editor: any = null;
	let monaco: any = null;
	let loading = $state(true);
	let error = $state('');
	let lastPath = path;

	const LANG_MAP: Record<string,string> = { python:'python', javascript:'javascript', typescript:'typescript', dockerfile:'dockerfile', bash:'shell', json:'json', markdown:'markdown', yaml:'yaml', rust:'rust', go:'go', svelte:'html' };

	onMount(async () => {
		try {
			await new Promise<void>((res, rej) => {
				if ((window as any).require) return res();
				const s = document.createElement('script');
				s.src = 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.52.2/min/vs/loader.min.js';
				s.onload = () => res(); s.onerror = () => rej(new Error('Failed to load Monaco loader'));
				document.head.appendChild(s);
			});
			monaco = await new Promise((res, rej) => {
				(window as any).require.config({ paths:{ vs:'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.52.2/min/vs' } });
				(window as any).require(['vs/editor/editor.main'], res, rej);
			});
			const isDark = document.documentElement.classList.contains('dark');
			editor = monaco.editor.create(container, {
				value: content, language: LANG_MAP[language] ?? 'plaintext',
				theme: isDark ? 'vs-dark' : 'vs',
				fontSize: 13, fontFamily: "'JetBrains Mono','Fira Code',monospace", fontLigatures: true,
				lineNumbers: 'on', minimap: { enabled: false }, scrollBeyondLastLine: false,
				automaticLayout: true, tabSize: 4, padding: { top: 12, bottom: 12 },
				scrollbar: { verticalScrollbarSize: 6, horizontalScrollbarSize: 6 },
			});
			editor.onDidChangeModelContent(() => ideStore.updateFileContent(path, editor.getValue()));
			editor.onDidChangeCursorPosition((e: any) => document.dispatchEvent(new CustomEvent('ide:cursor', { detail: e.position })));
			new MutationObserver(() => monaco.editor.setTheme(document.documentElement.classList.contains('dark') ? 'vs-dark' : 'vs'))
				.observe(document.documentElement, { attributes:true, attributeFilter:['class'] });
			loading = false;
		} catch(e) { error = String(e); loading = false; }
	});

	$effect(() => {
		if (path !== lastPath && editor && monaco) {
			lastPath = path;
			editor.setModel(monaco.editor.createModel(content, LANG_MAP[language] ?? 'plaintext'));
		}
	});

	onDestroy(() => editor?.dispose());
	export function formatDocument() { editor?.getAction('editor.action.formatDocument')?.run(); }
	export function focus() { editor?.focus(); }
</script>

<div class="relative h-full w-full">
	{#if loading}
		<div class="flex h-full items-center justify-center text-muted-foreground">
			<div class="flex flex-col items-center gap-2">
				<div class="h-5 w-5 animate-spin rounded-full border-2 border-muted-foreground border-t-transparent"></div>
				<span class="text-xs">Loading Monaco editor…</span>
			</div>
		</div>
	{:else if error}
		<div class="flex h-full items-center justify-center p-8">
			<div class="rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm">
				<p class="font-medium text-destructive">Editor failed to load</p>
				<p class="mt-1 font-mono text-xs text-muted-foreground">{error}</p>
			</div>
		</div>
	{/if}
	<div bind:this={container} class="h-full w-full" class:opacity-0={loading || !!error}></div>
</div>
