class TokenStore {
  constructor() {
    this.tokens = null;
  }

  set(tokens) {
    const next = { ...tokens };
    if (!next.refresh_token && this.tokens?.refresh_token) {
      next.refresh_token = this.tokens.refresh_token;
    }
    this.tokens = next;
  }

  get() {
    return this.tokens;
  }

  hasTokens() {
    return Boolean(this.tokens?.access_token || this.tokens?.refresh_token);
  }
}

export const tokenStore = new TokenStore();
