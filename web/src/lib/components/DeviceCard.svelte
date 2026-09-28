<script lang="ts">
	import { resolve } from '$app/paths';
	import {
		checkDeviceAvailability,
		getHardware,
		getStatus,
		getSystemInfo,
		Role,
		type Hardware,
		type SystemInfo
	} from '$lib/recorder';
	import type { User } from 'firebase/auth';

	interface Props {
		name: string;
		allowed_roles: Role[];
		active: boolean;
		location: string | null;
		user: User;
	}

	let { user, name, allowed_roles = $bindable(), active, location }: Props = $props();
	const status_promise = getStatus(user, name);
	const local_promise = checkDeviceAvailability(name);
	const system_promise = active ? getSystemInfo(user, name) : null;
	const hardware_promise = active ? getHardware(user, name) : null;

	const hardwareRows = (hardware: Hardware): [string, string][] => {
		const sensors = [
			...(hardware.temperature_humidity ? ['Temperatur', 'Luftfuktighet'] : []),
			...(hardware.cpu_temperature ? ['CPU-temperatur'] : [])
		];
		return [
			['Sensorer', sensors.length > 0 ? sensors.join(', ') : 'Inga'],
			['Kamera', hardware.camera ? 'Ja' : 'Nej'],
			['Mikrofon', hardware.microphone ?? 'Nej']
		];
	};

	const formatBytes = (bytes: number): string => {
		const gigabytes = bytes / 1024 ** 3;
		return gigabytes >= 1 ? `${gigabytes.toFixed(1)} GB` : `${Math.round(bytes / 1024 ** 2)} MB`;
	};

	const formatUsage = (total: number | null, available: number | null): string | null =>
		total && available !== null
			? `${formatBytes(total - available)} / ${formatBytes(total)}`
			: null;

	const formatUptime = (boot_time: string | null): string | null => {
		if (!boot_time) {
			return null;
		}
		const minutes = Math.floor((Date.now() - new Date(boot_time).getTime()) / 60000);
		const days = Math.floor(minutes / (60 * 24));
		const hours = Math.floor((minutes % (60 * 24)) / 60);
		if (days > 0) {
			return `${days} d ${hours} h`;
		}
		return hours > 0 ? `${hours} h ${minutes % 60} min` : `${minutes} min`;
	};

	const systemRows = (info: SystemInfo): [string, string][] =>
		(
			[
				['Modell', info.model],
				['OS', info.os],
				['Kärna', info.kernel && `${info.kernel} (${info.architecture ?? '?'})`],
				['Uppe', formatUptime(info.boot_time)],
				['Minne', formatUsage(info.memory_total, info.memory_available)],
				['Disk', formatUsage(info.disk_total, info.disk_free)],
				['Version', info.commit]
			] as [string, string | null][]
		).filter((row): row is [string, string] => !!row[1]);
</script>

<a
	class="rounded-lg border border-gray-300 p-4 text-left"
	href={resolve('/device') + `?name=${name}`}
>
	<div class="flex items-center justify-between">
		<div class="text-xl font-semibold">{name}</div>
		{#await local_promise then local}
			{#if active}
				<div class="rounded bg-green-100 px-2 py-1 text-sm font-medium text-green-800">
					Aktiv {local ? '(Lokal)' : '(Fjärr)'}
				</div>
			{:else}
				<div class="rounded bg-gray-100 px-2 py-1 text-sm font-medium text-gray-800">
					Inaktiv {local ? '(Lokal)' : '(Fjärr)'}
				</div>
			{/if}
		{/await}
	</div>
	<div class="mt-2 text-gray-600">Plats: {location ?? 'Ingen'}</div>
	{#if active}
		{#await status_promise}
			<div class="rounded-log mt-3 mb-3 h-4 w-24 animate-pulse rounded bg-gray-300"></div>
		{:then status}
			<div class="mt-2 text-gray-600">Status: {status.status ?? 'Okänd'}</div>
		{/await}
		{#await hardware_promise then hardware}
			{#if hardware}
				<dl class="mt-3 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
					{#each hardwareRows(hardware) as [label, value] (label)}
						<dt class="text-gray-500">{label}</dt>
						<dd class="break-words text-gray-800">{value}</dd>
					{/each}
				</dl>
			{/if}
		{:catch}
			<!-- Devices running an older version don't have the endpoint yet -->
		{/await}
		{#await system_promise then info}
			{#if info}
				<dl class="mt-3 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
					{#each systemRows(info) as [label, value] (label)}
						<dt class="text-gray-500">{label}</dt>
						<dd class="break-words text-gray-800">{value}</dd>
					{/each}
				</dl>
			{/if}
		{:catch}
			<!-- Devices running an older version don't have the endpoint yet -->
		{/await}
	{/if}
</a>
