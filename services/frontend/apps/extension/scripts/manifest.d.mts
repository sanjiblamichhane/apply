export const BOARD_HOSTS: string[];
export const API_HOSTS: string[];
export function manifest(options: { version: string; testHosts?: string[] }): {
  manifest_version: number;
  permissions: string[];
  host_permissions: string[];
  optional_host_permissions: string[];
  content_scripts: { matches: string[]; js: string[] }[];
  [key: string]: unknown;
};
export const ICON_SIZES: number[];
