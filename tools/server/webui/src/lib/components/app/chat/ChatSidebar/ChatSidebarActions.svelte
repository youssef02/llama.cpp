<script lang="ts">
	import { Search, SquarePen, X, Package, Code2 } from '@lucide/svelte';
	import { KeyboardShortcutInfo } from '$lib/components/app';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { page } from '$app/state';
	import { routerModels } from '$lib/stores/models.svelte';
	import { serverStore } from '$lib/stores/server.svelte';
	import { ServerModelStatus } from '$lib/enums';

	interface Props {
		handleMobileSidebarItemClick: () => void;
		isSearchModeActive: boolean;
		searchQuery: string;
	}

	let {
		handleMobileSidebarItemClick,
		isSearchModeActive = $bindable(),
		searchQuery = $bindable()
	}: Props = $props();

	let loadedCount = $derived(
		routerModels().filter((m) => m.status?.value === ServerModelStatus.LOADED).length
	);

	let searchInput: HTMLInputElement | null = $state(null);

	function handleSearchModeDeactivate() {
		isSearchModeActive = false;
		searchQuery = '';
	}

	$effect(() => {
		if (isSearchModeActive) {
			searchInput?.focus();
		}
	});
</script>

<div class="space-y-1">
	{#if isSearchModeActive}
		<div class="relative">
			<Search class="absolute top-2.5 left-3 h-4 w-4 text-muted-foreground" />

			<Input
				bind:ref={searchInput}
				bind:value={searchQuery}
				onkeydown={(e) => e.key === 'Escape' && handleSearchModeDeactivate()}
				placeholder="Search conversations..."
				class="pl-9 pr-9 rounded-xl bg-accent/50 border-border/20 focus:bg-background text-sm"
			/>

			<button
				class="absolute top-2.5 right-2.5 flex h-4 w-4 items-center justify-center rounded-sm text-muted-foreground hover:text-foreground"
				onclick={handleSearchModeDeactivate}
			>
				<X class="h-3.5 w-3.5" />
			</button>
		</div>
	{:else}
		<Button
			class="w-full justify-between rounded-xl font-medium hover:[&>kbd]:opacity-100"
			href="?new_chat=true#/"
			onclick={handleMobileSidebarItemClick}
			variant="ghost"
		>
			<div class="flex items-center gap-2.5">
				<SquarePen class="h-4 w-4 text-primary/70" />
				New chat
			</div>

			<KeyboardShortcutInfo keys={['shift', 'cmd', 'o']} />
		</Button>

		<Button
			class="w-full justify-start gap-2.5 rounded-xl font-medium {page.route.id === '/models' ? 'bg-primary/10 text-primary' : ''}"
			href="#/models"
			onclick={handleMobileSidebarItemClick}
			variant="ghost"
		>
			<Package class="h-4 w-4 {page.route.id === '/models' ? 'text-primary' : 'text-muted-foreground'}" />
			Models
			{#if serverStore.isRouterMode && loadedCount > 0}
				<span class="ml-auto flex h-5 min-w-5 items-center justify-center rounded-full bg-green-500/15 px-1.5 text-[10px] font-semibold text-green-500">{loadedCount}</span>
			{/if}
		</Button>

		<Button
			class="w-full justify-start gap-2.5 rounded-xl font-medium {page.route.id === '/ide' ? 'bg-primary/10 text-primary' : ''}"
			href="#/ide"
			onclick={handleMobileSidebarItemClick}
			variant="ghost"
		>
			<Code2 class="h-4 w-4 {page.route.id === '/ide' ? 'text-primary' : 'text-muted-foreground'}" />
			IDE
		</Button>

		<Button
			class="w-full justify-between rounded-xl font-medium hover:[&>kbd]:opacity-100"
			onclick={() => {
				isSearchModeActive = true;
			}}
			variant="ghost"
		>
			<div class="flex items-center gap-2.5">
				<Search class="h-4 w-4 text-muted-foreground" />
				Search
			</div>

			<KeyboardShortcutInfo keys={['cmd', 'k']} />
		</Button>
	{/if}
</div>
