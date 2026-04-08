import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { App } from './App';
import './index.css';

class RootErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, errorMessage: '' };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, errorMessage: error?.message || 'Unexpected UI error' };
  }

  componentDidCatch(error, info) {
    // Keep console visibility for debugging while showing a friendly UI fallback.
    console.error('Root render error', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ minHeight: '100vh', background: '#08111f', color: '#e2e8f0', padding: '2rem', fontFamily: 'ui-sans-serif, system-ui' }}>
          <h1 style={{ fontSize: '1.25rem', marginBottom: '0.75rem' }}>Frontend runtime error</h1>
          <p style={{ marginBottom: '0.5rem' }}>The app hit an unexpected error instead of rendering a blank page.</p>
          <pre style={{ whiteSpace: 'pre-wrap', opacity: 0.9 }}>{this.state.errorMessage}</pre>
        </div>
      );
    }
    return this.props.children;
  }
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <RootErrorBoundary>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </RootErrorBoundary>
  </React.StrictMode>,
);
