/**
 * IDE Store — editor tabs, Podman containers, terminal, file tree
 */
import { browser } from '$app/environment';

export interface EditorFile { path: string; name: string; language: string; content: string; isDirty: boolean; }
export interface PodmanContainer { id: string; name: string; image: string; status: 'running'|'stopped'|'building'|'error'; cpuPercent?: number; memoryMB?: number; uptimeSeconds?: number; ports?: string[]; }
export interface TerminalLine { id: string; type: 'command'|'stdout'|'stderr'|'info'|'success'; text: string; }
export interface FileTreeNode { name: string; path: string; type: 'file'|'directory'; language?: string; children?: FileTreeNode[]; expanded?: boolean; }

const EXT: Record<string, string> = { py:'python', js:'javascript', ts:'typescript', svelte:'svelte', html:'html', css:'css', json:'json', md:'markdown', sh:'bash', dockerfile:'dockerfile', yaml:'yaml', yml:'yaml', rs:'rust', go:'go' };
export function detectLanguage(f: string): string {
	const l = f.toLowerCase();
	if (l === 'dockerfile') return 'dockerfile';
	return EXT[f.split('.').pop()?.toLowerCase() ?? ''] ?? 'plaintext';
}

const SAMPLE: EditorFile[] = [
	{ path:'main.py', name:'main.py', language:'python', isDirty:false, content:`import json\nfrom typing import Generator\n\n\ndef batch_jsonl(\n    filepath: str,\n    batch_size: int = 100,\n) -> Generator[list[dict], None, None]:\n    """Read a JSONL file and yield batches."""\n    batch: list[dict] = []\n    with open(filepath, "r", encoding="utf-8") as f:\n        for line in f:\n            line = line.strip()\n            if not line:\n                continue\n            try:\n                batch.append(json.loads(line))\n                if len(batch) >= batch_size:\n                    yield batch\n                    batch = []\n            except json.JSONDecodeError as e:\n                print(f"Skipping: {e}")\n    if batch:\n        yield batch\n\n\nif __name__ == "__main__":\n    import sys\n    for b in batch_jsonl(sys.argv[1] if len(sys.argv) > 1 else "data.jsonl"):\n        print(f"  batch: {len(b)}")\n` },
	{ path:'Dockerfile', name:'Dockerfile', language:'dockerfile', isDirty:false, content:`FROM python:3.12-slim\nWORKDIR /app\nCOPY requirements.txt .\nRUN pip install --no-cache-dir -r requirements.txt\nCOPY . .\nEXPOSE 8000\nCMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]\n` },
];

function createIdeStore() {
	let openFiles    = $state<EditorFile[]>(SAMPLE.slice(0,1));
	let activeFilePath = $state(SAMPLE[0].path);
	let fileTree     = $state<FileTreeNode[]>([{ name:'project', path:'.', type:'directory', expanded:true, children: SAMPLE.map((f)=>({ name:f.name, path:f.path, type:'file' as const, language:f.language })) }]);
	let containers   = $state<PodmanContainer[]>([]);
	let podmanAvailable = $state(false);
	let terminalLines = $state<TerminalLine[]>([{ id:crypto.randomUUID(), type:'info', text:'Terminal ready. Start the IDE sidecar to run code in Podman containers.', }]);
	let terminalInput = $state('');
	let activeBottomPanel = $state<'terminal'|'output'|'problems'>('terminal');
	let bottomPanelOpen = $state(true);

	const activeFile = $derived(openFiles.find((f) => f.path === activeFilePath) ?? null);

	function openFile(path: string) {
		if (openFiles.find((f) => f.path === path)) { activeFilePath = path; return; }
		const s = SAMPLE.find((f) => f.path === path);
		openFiles = [...openFiles, s ?? { path, name:path.split('/').pop()??path, language:detectLanguage(path), content:'', isDirty:false }];
		activeFilePath = path;
	}
	function closeFile(path: string) {
		openFiles = openFiles.filter((f) => f.path !== path);
		if (activeFilePath === path) activeFilePath = openFiles.at(-1)?.path ?? '';
	}
	function updateFileContent(path: string, content: string) {
		openFiles = openFiles.map((f) => f.path === path ? {...f, content, isDirty:true} : f);
	}
	function saveFile(path: string) {
		openFiles = openFiles.map((f) => f.path === path ? {...f, isDirty:false} : f);
		addTerminalLine('info', `Saved ${path}`);
	}

	async function checkPodmanApi() {
		if (!browser) return;
		try {
			const r = await fetch('/ide/health', { signal: AbortSignal.timeout(1500) });
			if (r.ok) {
				const d = await r.json();
				podmanAvailable = d.podman === true;
				if (podmanAvailable) {
					const cr = await fetch('/ide/containers');
					if (cr.ok) containers = await cr.json();
				}
			} else { podmanAvailable = false; }
		} catch { podmanAvailable = false; }
	}

	async function startContainer(id: string) {
		containers = containers.map((c) => c.id===id ? {...c, status:'building'} : c);
		addTerminalLine('command', `podman start ${id}`);
		try { await fetch(`/ide/containers/${id}/start`, { method:'POST' }); } catch {}
		setTimeout(() => { containers = containers.map((c) => c.id===id ? {...c,status:'running',cpuPercent:0.1,memoryMB:32,uptimeSeconds:0} : c); addTerminalLine('success', `${id} started`); }, 1200);
	}
	async function stopContainer(id: string) {
		addTerminalLine('command', `podman stop ${id}`);
		try { await fetch(`/ide/containers/${id}/stop`, { method:'POST' }); } catch {}
		containers = containers.map((c) => c.id===id ? {...c,status:'stopped',cpuPercent:undefined,memoryMB:undefined} : c);
		addTerminalLine('success', `${id} stopped`);
	}
	async function removeContainer(id: string) {
		try { await fetch(`/ide/containers/${id}`, { method:'DELETE' }); } catch {}
		containers = containers.filter((c) => c.id!==id);
		addTerminalLine('info', `${id} removed`);
	}
	async function createContainer(opts: { name:string; image:string; ports?:string; mountPath?:string; env?:string; cmd?:string }) {
		containers = [...containers, { id:opts.name, name:opts.name, image:opts.image, status:'building' }];
		addTerminalLine('command', `podman run -d --name ${opts.name} ${opts.image}`);
		try { await fetch('/ide/containers', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(opts) }); } catch {}
		setTimeout(() => { containers = containers.map((c) => c.id===opts.name ? {...c,status:'running',cpuPercent:0.1,memoryMB:32,uptimeSeconds:0} : c); addTerminalLine('success', `${opts.name} running`); }, 2000);
	}
	async function execInContainer(containerId: string, code: string, language: string) {
		addTerminalLine('command', `exec in ${containerId} (${language})`);
		activeBottomPanel = 'terminal'; bottomPanelOpen = true;
		try {
			const r = await fetch('/ide/containers/exec', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({ containerId, code, language }) });
			if (!r.ok) throw new Error(`HTTP ${r.status}`);
			const d = await r.json();
			(d.stdout||'').split('\n').filter(Boolean).forEach((l: string) => addTerminalLine('stdout', l));
			(d.stderr||'').split('\n').filter(Boolean).forEach((l: string) => addTerminalLine('stderr', l));
			addTerminalLine('success', `Exit ${d.exitCode ?? 0} · ${d.durationMs?.toFixed(0) ?? '?'}ms`);
		} catch (e) { addTerminalLine('stderr', `Error: ${e}`); }
	}

	function addTerminalLine(type: TerminalLine['type'], text: string) {
		terminalLines = [...terminalLines, { id:crypto.randomUUID(), type, text }];
	}
	function clearTerminal() { terminalLines = []; }

	return {
		get openFiles() { return openFiles; },
		get activeFilePath() { return activeFilePath; },
		get activeFile() { return activeFile; },
		get fileTree() { return fileTree; },
		get containers() { return containers; },
		get podmanAvailable() { return podmanAvailable; },
		get terminalLines() { return terminalLines; },
		get terminalInput() { return terminalInput; },
		set terminalInput(v) { terminalInput = v; },
		get activeBottomPanel() { return activeBottomPanel; },
		set activeBottomPanel(v: typeof activeBottomPanel) { activeBottomPanel = v; },
		get bottomPanelOpen() { return bottomPanelOpen; },
		set bottomPanelOpen(v) { bottomPanelOpen = v; },
		openFile, closeFile, updateFileContent, saveFile,
		checkPodmanApi, startContainer, stopContainer, removeContainer, createContainer, execInContainer,
		addTerminalLine, clearTerminal,
	};
}

export const ideStore = createIdeStore();
