<script lang="ts">
	import { ServerModelStatus } from '$lib/enums';
	interface Props { status: string | null | undefined; class?: string; }
	let { status, class: cls = '' }: Props = $props();
	const cfg: Record<string, { dot: string; label: string; pill: string }> = {
		[ServerModelStatus.LOADED]:   { dot: 'bg-green-400 shadow-[0_0_5px] shadow-green-400/60', label: 'loaded',   pill: 'bg-green-500/10 text-green-500' },
		[ServerModelStatus.LOADING]:  { dot: 'animate-pulse bg-yellow-400',                       label: 'loading',  pill: 'bg-yellow-500/10 text-yellow-500' },
		[ServerModelStatus.UNLOADED]: { dot: 'bg-muted-foreground/30',                             label: 'unloaded', pill: 'bg-muted text-muted-foreground' },
		[ServerModelStatus.FAILED]:   { dot: 'bg-destructive',                                     label: 'failed',   pill: 'bg-destructive/10 text-destructive' },
	};
	let c = $derived(cfg[status ?? ''] ?? cfg[ServerModelStatus.UNLOADED]);
</script>
<span class="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide {c.pill} {cls}">
	<span class="h-1.5 w-1.5 flex-shrink-0 rounded-full {c.dot}"></span>{c.label}
</span>
