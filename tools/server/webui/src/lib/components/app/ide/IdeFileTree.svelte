<script lang="ts">
	import { ChevronRight, ChevronDown, File, Folder, FolderOpen } from '@lucide/svelte';
	import { ideStore, type FileTreeNode } from '$lib/stores/ide.svelte';
	const COLORS: Record<string,string> = { python:'text-blue-400', javascript:'text-yellow-400', typescript:'text-blue-500', dockerfile:'text-sky-400', json:'text-yellow-300', markdown:'text-purple-400', bash:'text-green-400', rust:'text-orange-500', go:'text-cyan-400' };
</script>
<div class="select-none py-1">
	{#each ideStore.fileTree as node (node.path)}
		{@render TreeNode(node, 0)}
	{/each}
</div>
{#snippet TreeNode(node: FileTreeNode, depth: number)}
	{#if node.type === 'directory'}
		<button class="flex w-full items-center gap-1.5 rounded px-2 py-0.5 text-left text-xs text-muted-foreground hover:bg-accent"
			style="padding-left:{depth*12+8}px" onclick={() => { node.expanded = !node.expanded; }}>
			{#if node.expanded}<ChevronDown class="h-3 w-3 flex-shrink-0" /><FolderOpen class="h-3.5 w-3.5 flex-shrink-0 text-yellow-400" />
			{:else}<ChevronRight class="h-3 w-3 flex-shrink-0" /><Folder class="h-3.5 w-3.5 flex-shrink-0 text-yellow-400" />{/if}
			<span class="truncate">{node.name}</span>
		</button>
		{#if node.expanded && node.children}
			{#each node.children as child (child.path)}{@render TreeNode(child, depth+1)}{/each}
		{/if}
	{:else}
		<button class="flex w-full items-center gap-1.5 rounded px-2 py-0.5 text-left text-xs transition-colors
			{ideStore.activeFilePath === node.path ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'}"
			style="padding-left:{depth*12+8}px" onclick={() => ideStore.openFile(node.path)}>
			<File class="h-3.5 w-3.5 flex-shrink-0 {COLORS[node.language??''] ?? 'text-muted-foreground'}" />
			<span class="truncate">{node.name}</span>
			{#if ideStore.openFiles.find((f) => f.path===node.path)?.isDirty}
				<span class="ml-auto h-1.5 w-1.5 flex-shrink-0 rounded-full bg-primary"></span>
			{/if}
		</button>
	{/if}
{/snippet}
