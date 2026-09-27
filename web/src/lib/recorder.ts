import type { User } from 'firebase/auth';
import { authorizedRequest } from './request';
import { PUBLIC_RECORDER_URL } from '$env/static/public';

export enum Role {
	ADMIN = 'admin',
	USER = 'user'
}

export const getRole = async (u: User): Promise<Role | null> => {
	const response = await authorizedRequest(u, PUBLIC_RECORDER_URL, 'me');
	if (!response.ok) {
		return null;
	}
	const data = await response.json();
	const role = data.role;
	if (role === Role.ADMIN) return Role.ADMIN;
	if (role === Role.USER) return Role.USER;
	return null;
};

export const getUsers = async (
	u: User
): Promise<{ id: string; email: string; role: Role | null; provider: string | null }[] | null> => {
	const response = await authorizedRequest(u, PUBLIC_RECORDER_URL, 'users');
	if (!response.ok) {
		return null;
	}
	const data = await response.json();
	return data.map(
		(entry: { id: string; email: string; role: string; provider: string | null }) => ({
			id: entry.id,
			email: entry.email,
			role: entry.role ? (entry.role === Role.ADMIN ? Role.ADMIN : Role.USER) : null,
			provider: entry.provider
		})
	);
};

export const setUserRole = async (user: User, id: string, role: Role | null): Promise<void> => {
	const response = await authorizedRequest(
		user,
		PUBLIC_RECORDER_URL,
		`set_user_role/${id}`,
		'POST',
		{ role },
		{
			'Content-Type': 'application/json'
		}
	);
	await response.json();
};

export interface Recording {
	url: string;
	created_at: Date;
}

export const getRecordings = async (
	user: User,
	device_name: string,
	from?: Date,
	to?: Date
): Promise<Recording[]> => {
	let url_params = new URLSearchParams();
	if (from) {
		url_params.append('from', from.toISOString());
	}
	if (to) {
		url_params.append('to', to.toISOString());
	}
	const url = `recordings/${device_name}?${url_params.toString()}`;
	const response = await authorizedRequest(user, PUBLIC_RECORDER_URL, url);
	const data = await response.json();
	return data.map((entry: { url: string; created_at: string }) => ({
		url: entry.url,
		created_at: new Date(entry.created_at)
	}));
};

export interface SensorData {
	created_at: Date;
	temperature?: number;
	humidity?: number;
	cpu_temperature?: number;
}

export const getSensorData = async (
	user: User,
	device_name: string,
	from?: Date,
	to?: Date
): Promise<SensorData[]> => {
	let url_params = new URLSearchParams();
	if (from) {
		url_params.append('from', from.toISOString());
	}
	if (to) {
		url_params.append('to', to.toISOString());
	}
	const url = `sensors/${device_name}?${url_params.toString()}`;
	const response = await authorizedRequest(user, PUBLIC_RECORDER_URL, url);
	const data = await response.json();
	return data.map(
		(entry: {
			created_at: string;
			temperature: number | null;
			humidity: number | null;
			cpu_temperature: number | null;
		}) => ({
			created_at: new Date(entry.created_at),
			...(entry.temperature != null && { temperature: entry.temperature }),
			...(entry.humidity != null && { humidity: entry.humidity }),
			...(entry.cpu_temperature != null && { cpu_temperature: entry.cpu_temperature })
		})
	);
};

export interface Location {
	id: string;
	name: string;
	current_device_name: string | null;
}

export const getLocations = async (user: User): Promise<Location[]> => {
	const response = await authorizedRequest(user, PUBLIC_RECORDER_URL, 'locations');
	return response.json();
};

export const getSensorDataByLocation = async (
	user: User,
	location_name: string,
	from?: Date,
	to?: Date
): Promise<SensorData[]> => {
	const url_params = new URLSearchParams();
	if (from) url_params.append('from', from.toISOString());
	if (to) url_params.append('to', to.toISOString());
	const url = `sensors_by_location/${location_name}?${url_params.toString()}`;
	const response = await authorizedRequest(user, PUBLIC_RECORDER_URL, url);
	const data = await response.json();
	return data.map(
		(entry: {
			created_at: string;
			temperature: number | null;
			humidity: number | null;
			cpu_temperature: number | null;
		}) => ({
			created_at: new Date(entry.created_at),
			...(entry.temperature != null && { temperature: entry.temperature }),
			...(entry.humidity != null && { humidity: entry.humidity }),
			...(entry.cpu_temperature != null && { cpu_temperature: entry.cpu_temperature })
		})
	);
};

export const getRecordingsByLocation = async (
	user: User,
	location_name: string,
	from?: Date,
	to?: Date
): Promise<Recording[]> => {
	const url_params = new URLSearchParams();
	if (from) url_params.append('from', from.toISOString());
	if (to) url_params.append('to', to.toISOString());
	const url = `recordings_by_location/${location_name}?${url_params.toString()}`;
	const response = await authorizedRequest(user, PUBLIC_RECORDER_URL, url);
	const data = await response.json();
	return data.map((entry: { url: string; created_at: string }) => ({
		url: entry.url,
		created_at: new Date(entry.created_at)
	}));
};

export const listDevices = async (
	user: User
): Promise<{ name: string; allowed_roles: Role[]; active: boolean }[]> => {
	const response = await authorizedRequest(user, PUBLIC_RECORDER_URL, 'list_devices');
	return response.json();
};

export const getDevice = async (
	user: User,
	device_name: string
): Promise<{ name: string; allowed_roles: Role[]; active: boolean } | null> => {
	const response = await authorizedRequest(user, PUBLIC_RECORDER_URL, `device/${device_name}`);
	if (!response.ok) {
		return null;
	}
	return response.json();
};

export const setDeviceRoles = async (
	user: User,
	device_name: string,
	roles: Role[]
): Promise<void> => {
	const response = await authorizedRequest(
		user,
		PUBLIC_RECORDER_URL,
		`set_roles/${device_name}`,
		'POST',
		roles,
		{
			'Content-Type': 'application/json'
		}
	);
	await response.json();
};

export const getStatus = async (user: User, device_name: string): Promise<{ status: string }> => {
	const { response } = await localRequestWithRelayFallback(user, device_name, `/status`);
	return response.json();
};

export type SystemInfo = {
	hostname: string | null;
	model: string | null;
	os: string | null;
	kernel: string | null;
	architecture: string | null;
	python: string | null;
	commit: string | null;
	boot_time: string | null;
	load_average: [number, number, number] | null;
	memory_total: number | null;
	memory_available: number | null;
	disk_total: number | null;
	disk_free: number | null;
};

export const getSystemInfo = async (user: User, device_name: string): Promise<SystemInfo> => {
	const { response } = await localRequestWithRelayFallback(user, device_name, `/system`);
	if (!response.ok) {
		throw new Error(`Failed to get system info: ${response.status}`);
	}
	return response.json();
};

export const getCurrentSensorData = async (
	user: User,
	device_name: string
): Promise<SensorData> => {
	const { response } = await localRequestWithRelayFallback(user, device_name, `/sensor`);
	const sensor_data = await response.json();
	return {
		created_at: new Date(),
		temperature: sensor_data.temperature,
		humidity: sensor_data.humidity
	};
};

export const startAndGetStreamUrl = async (
	user: User,
	device_name: string
): Promise<string | null> => {
	const { response, base_url } = await localRequestWithRelayFallback(
		user,
		device_name,
		`/start?bitrate=500000&framerate=24`
	);
	if (!response.ok) {
		return null;
	}
	const playlist_endpoint = (await response.json()).playlist;
	return `${base_url}${playlist_endpoint}`;
};

export const localRequestWithRelayFallback = async (
	user: User,
	device_name: string,
	endpoint: string
): Promise<{ response: Response; base_url: string }> => {
	const base_url = (await checkDeviceAvailability(device_name))
		? `https://${device_name}.local`
		: `${PUBLIC_RECORDER_URL}get/${device_name}`;
	const response = await authorizedRequest(user, base_url, endpoint);
	return { response, base_url };
};

export const checkDeviceAvailability = async (device_name: string): Promise<boolean> => {
	const url = `https://${device_name}.local/status`;
	const controller = new AbortController();
	const timeoutId = setTimeout(() => controller.abort(), 500);
	try {
		await fetch(url, {
			method: 'GET',
			signal: controller.signal
		});
		return true;
	} catch (error: any) {
		if (error.name !== 'AbortError') {
			console.log(`⚠️ ${url} is unreachable, but DNS might have resolved.`);
		}
		return false;
	} finally {
		clearTimeout(timeoutId);
	}
};
