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

<div class="space-y-0.5">
	{#if isSearchModeActive}
		<div class="relative">
			<Search class="absolute top-2.5 left-2 h-4 w-4 text-muted-foreground" />

			<Input
				bind:ref={searchInput}
				bind:value={searchQuery}
				onkeydown={(e) => e.key === 'Escape' && handleSearchModeDeactivate()}
				placeholder="Search conversations..."
				class="pl-8"
			/>

			<X
				class="cursor-pointertext-muted-foreground absolute top-2.5 right-2 h-4 w-4"
				onclick={handleSearchModeDeactivate}
			/>
		</div>
	{:else}
		<Button
			class="w-full justify-between hover:[&>kbd]:opacity-100"
			href="?new_chat=true#/"
			onclick={handleMobileSidebarItemClick}
			variant="ghost"
		>
			<div class="flex items-center gap-2">
				<SquarePen class="h-4 w-4" />
				New chat
			</div>

			<KeyboardShortcutInfo keys={['shift', 'cmd', 'o']} />
		</Button>

		<Button
			class="w-full justify-start gap-2 {page.route.id === '/models' ? 'bg-accent' : ''}"
			href="#/models"
			onclick={handleMobileSidebarItemClick}
			variant="ghost"
		>
			<Package class="h-4 w-4" />
			Models
			{#if serverStore.isRouterMode && loadedCount > 0}
				<span class="ml-auto flex h-5 min-w-5 items-center justify-center rounded-full bg-green-500/15 px-1.5 text-[10px] font-semibold text-green-500">{loadedCount}</span>
			{/if}
		</Button>

		<Button
			class="w-full justify-start gap-2 {page.route.id === '/ide' ? 'bg-accent' : ''}"
			href="#/ide"
			onclick={handleMobileSidebarItemClick}
			variant="ghost"
		>
			<Code2 class="h-4 w-4" />
			IDE
		</Button>

		<Button
			class="w-full justify-between hover:[&>kbd]:opacity-100"
			onclick={() => {
				isSearchModeActive = true;
			}}
			variant="ghost"
		>
			<div class="flex items-center gap-2">
				<Search class="h-4 w-4" />
				Search conversations
			</div>

			<KeyboardShortcutInfo keys={['cmd', 'k']} />
		</Button>
	{/if}
</div>
