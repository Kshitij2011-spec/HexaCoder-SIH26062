/**
 * Client-Side Durable IndexedDB Outbox Store (A8).
 *
 * Database: polarops_sync_db
 * Object Store: outbox
 * Primary Key: client_operation_id (UUID v4)
 *
 * Provides persistent FIFO storage for offline operational mutations
 * during polar communications blackouts, surviving page reload and browser restarts.
 * Falls back to an in-memory store in headless/mock test environments.
 */

import type { OutboxOperation } from './types';

const DB_NAME = 'polarops_sync_db';
const DB_VERSION = 1;
const STORE_NAME = 'outbox';

// In-memory fallback for environments without IndexedDB (e.g. standard Node/jsdom test runs)
const memoryStore = new Map<string, OutboxOperation>();

function isIndexedDBAvailable(): boolean {
  return typeof window !== 'undefined' && typeof window.indexedDB !== 'undefined' && window.indexedDB !== null;
}

let dbInstance: IDBDatabase | null = null;
let dbPromise: Promise<IDBDatabase> | null = null;

function openOutboxDB(): Promise<IDBDatabase> {
  if (dbInstance) return Promise.resolve(dbInstance);
  if (dbPromise) return dbPromise;

  dbPromise = new Promise((resolve, reject) => {
    if (!isIndexedDBAvailable()) {
      return reject(new Error('IndexedDB unavailable in this runtime'));
    }

    const request = window.indexedDB.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        const store = db.createObjectStore(STORE_NAME, { keyPath: 'client_operation_id' });
        store.createIndex('local_status', 'local_status', { unique: false });
        store.createIndex('queued_at', 'queued_at', { unique: false });
      }
    };

    request.onsuccess = () => {
      dbInstance = request.result;
      dbInstance.onclose = () => {
        dbInstance = null;
        dbPromise = null;
      };
      resolve(dbInstance);
    };

    request.onerror = () => {
      dbPromise = null;
      reject(request.error || new Error('Failed to open polarops_sync_db IndexedDB'));
    };
  });

  return dbPromise;
}

export async function saveOperation(operation: OutboxOperation): Promise<void> {
  if (!isIndexedDBAvailable()) {
    memoryStore.set(operation.client_operation_id, { ...operation });
    return;
  }

  try {
    const db = await openOutboxDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction([STORE_NAME], 'readwrite');
      const store = tx.objectStore(STORE_NAME);
      const req = store.put(operation);
      req.onsuccess = () => resolve();
      req.onerror = () => reject(req.error || new Error('Failed to save operation to IndexedDB'));
    });
  } catch {
    // Graceful fallback to memory store if indexedDB execution throws
    memoryStore.set(operation.client_operation_id, { ...operation });
  }
}

export async function getOperation(client_operation_id: string): Promise<OutboxOperation | undefined> {
  if (!isIndexedDBAvailable()) {
    const item = memoryStore.get(client_operation_id);
    return item ? { ...item } : undefined;
  }

  try {
    const db = await openOutboxDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction([STORE_NAME], 'readonly');
      const store = tx.objectStore(STORE_NAME);
      const req = store.get(client_operation_id);
      req.onsuccess = () => resolve(req.result as OutboxOperation | undefined);
      req.onerror = () => reject(req.error || new Error(`Failed to get operation ${client_operation_id}`));
    });
  } catch {
    const item = memoryStore.get(client_operation_id);
    return item ? { ...item } : undefined;
  }
}

export async function getAllOperations(): Promise<OutboxOperation[]> {
  if (!isIndexedDBAvailable()) {
    return Array.from(memoryStore.values()).sort(
      (a, b) => new Date(b.queued_at).getTime() - new Date(a.queued_at).getTime()
    );
  }

  try {
    const db = await openOutboxDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction([STORE_NAME], 'readonly');
      const store = tx.objectStore(STORE_NAME);
      const req = store.getAll();
      req.onsuccess = () => {
        const list = (req.result || []) as OutboxOperation[];
        list.sort((a, b) => new Date(b.queued_at).getTime() - new Date(a.queued_at).getTime());
        resolve(list);
      };
      req.onerror = () => reject(req.error || new Error('Failed to retrieve all operations'));
    });
  } catch {
    return Array.from(memoryStore.values()).sort(
      (a, b) => new Date(b.queued_at).getTime() - new Date(a.queued_at).getTime()
    );
  }
}

export async function getQueuedOperations(): Promise<OutboxOperation[]> {
  const all = await getAllOperations();
  // Filter for operations awaiting replay (LOCAL_QUEUED) or retryable (FAILED)
  return all
    .filter((op) => op.local_status === 'LOCAL_QUEUED' || op.local_status === 'FAILED')
    .sort((a, b) => new Date(a.queued_at).getTime() - new Date(b.queued_at).getTime()); // FIFO order
}

export async function updateOperationStatus(
  client_operation_id: string,
  updates: Partial<Pick<OutboxOperation, 'local_status' | 'retry_count' | 'last_error' | 'server_record_id' | 'applied_at'>>
): Promise<void> {
  const current = await getOperation(client_operation_id);
  if (!current) return;

  const merged: OutboxOperation = {
    ...current,
    ...updates,
  };

  await saveOperation(merged);
}

export async function deleteOperation(client_operation_id: string): Promise<void> {
  if (!isIndexedDBAvailable()) {
    memoryStore.delete(client_operation_id);
    return;
  }

  try {
    const db = await openOutboxDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction([STORE_NAME], 'readwrite');
      const store = tx.objectStore(STORE_NAME);
      const req = store.delete(client_operation_id);
      req.onsuccess = () => resolve();
      req.onerror = () => reject(req.error || new Error(`Failed to delete operation ${client_operation_id}`));
    });
  } catch {
    memoryStore.delete(client_operation_id);
  }
}

export async function clearAppliedOperations(): Promise<void> {
  const all = await getAllOperations();
  const applied = all.filter((op) => op.local_status === 'APPLIED');
  for (const op of applied) {
    await deleteOperation(op.client_operation_id);
  }
}

export async function resetStoreForTesting(): Promise<void> {
  memoryStore.clear();

  if (isIndexedDBAvailable()) {
    try {
      if (dbInstance) {
        dbInstance.close();
        dbInstance = null;
        dbPromise = null;
      }
      return new Promise((resolve) => {
        const req = window.indexedDB.deleteDatabase(DB_NAME);
        req.onsuccess = () => resolve();
        req.onerror = () => resolve();
        req.onblocked = () => resolve();
      });
    } catch {
      // Ignore errors in test teardown
    }
  }
}
