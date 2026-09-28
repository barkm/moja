<script lang="ts">
	import { listDevices as listRecordedDevices } from '$lib/recorder';
	import type { User } from 'firebase/auth';
	import DeviceCard from './DeviceCard.svelte';

	interface Props {
		user: User;
	}

	const { user }: Props = $props();

	const devices_promise = listRecordedDevices(user);
</script>

<div class="flex flex-col gap-4">
	{#await devices_promise}
		{#each Array(3) as _}
			<div class="animate-pulse rounded-lg bg-gray-100 p-4">
				<div class="h-6 w-1/3 rounded bg-gray-300"></div>
				<div class="mt-2 h-4 w-1/2 rounded bg-gray-300"></div>
			</div>
		{/each}
	{:then devices}
		{#each devices as device}
			<DeviceCard
				{user}
				name={device.name}
				allowed_roles={device.allowed_roles}
				active={device.active}
				location={device.location}
			/>
		{/each}
	{/await}
</div>
