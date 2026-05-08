/**
 * API client to interact with the backend through Next.js /api rewrite proxy.
 * Because we use httpOnly cookies, we do not need to manually pass Bearer tokens here.
 * The browser automatically includes cookies in requests to the same origin (/api/*).
 */

export const api = {
  async get(endpoint: string) {
    const res = await fetch(`/api${endpoint}`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });
    if (!res.ok) {
      throw new Error(`GET ${endpoint} failed: ${res.statusText}`);
    }
    return res.json();
  },

  async post(endpoint: string, body: any) {
    const res = await fetch(`/api${endpoint}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      let errorMessage = `POST ${endpoint} failed`;
      if (err.detail) {
        if (typeof err.detail === "string") {
          errorMessage = err.detail;
        } else if (Array.isArray(err.detail)) {
          errorMessage = err.detail.map((e: any) => e.msg).join(", ");
        } else {
          errorMessage = JSON.stringify(err.detail);
        }
      }
      throw new Error(errorMessage);
    }
    return res.json();
  },

  async postForm(endpoint: string, formData: FormData) {
    const res = await fetch(`/api${endpoint}`, {
      method: "POST",
      // Do not set Content-Type, browser will automatically set multipart/form-data with boundary
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      let errorMessage = `POST ${endpoint} failed`;
      if (err.detail) {
        if (typeof err.detail === "string") {
          errorMessage = err.detail;
        } else if (Array.isArray(err.detail)) {
          errorMessage = err.detail.map((e: any) => e.msg).join(", ");
        } else {
          errorMessage = JSON.stringify(err.detail);
        }
      }
      throw new Error(errorMessage);
    }
    return res.json();
  },

  async delete(endpoint: string) {
    const res = await fetch(`/api${endpoint}`, {
      method: "DELETE",
    });
    if (!res.ok) {
      throw new Error(`DELETE ${endpoint} failed: ${res.statusText}`);
    }
    return res.json();
  },
};
