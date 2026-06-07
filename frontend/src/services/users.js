/** 运行时必需。用户注册/登录与档案同步到 Flask。 */
import { createUser, listUsers, updateUser } from './api.js';
import { getCurrentUserId, loginSession, setCurrentUserId } from '../stores/storage.js';

function normalizeName(value) {
  return String(value || '').trim().split(/\s+/).filter(Boolean).join(' ');
}

export async function fetchAllUsers() {
  const payload = await listUsers();
  return Array.isArray(payload.items) ? payload.items : [];
}

export async function findUserByName(name) {
  const target = normalizeName(name);
  if (!target) return null;
  const users = await fetchAllUsers();
  return users.find((user) => normalizeName(user.name) === target) || null;
}

export async function registerOrLoginByName(name, profile = {}) {
  const displayName = normalizeName(name) || '训练用户';
  let user = await findUserByName(displayName);
  if (!user) {
    const created = await createUser({
      name: displayName,
      age: profile.age,
      heightCm: profile.heightCm,
      weightKg: profile.weightKg,
      hand: profile.hand || 'right',
      years: profile.years ?? 0,
      level: profile.level || 'amateur',
    });
    user = created.user;
  }
  return user;
}

export async function syncUserProfile(userId, profile) {
  if (!userId) return null;
  const payload = await updateUser(userId, {
    name: profile.name,
    age: profile.age,
    heightCm: profile.heightCm,
    weightKg: profile.weightKg,
    hand: profile.hand || 'right',
    years: profile.years ?? 0,
    level: profile.level || 'amateur',
  });
  return payload.user || null;
}

/** Ensure a valid user id: auto-pick first user or signal redirect to auth. */
export async function ensureCurrentUserForApp() {
  const users = await fetchAllUsers();
  if (!users.length) {
    return false;
  }
  let userId = getCurrentUserId();
  const valid = userId && users.some((user) => user.id === userId);
  if (!valid) {
    userId = users[0].id;
    setCurrentUserId(userId);
    loginSession(users[0].name || '训练用户', userId);
  }
  return true;
}
