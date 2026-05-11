import { useState } from 'react';

interface AddServerFormProps {
  onSubmit: (data: { name: string; url: string; email: string }) => Promise<void>;
}

export default function AddServerForm({ onSubmit }: AddServerFormProps) {
  const [formData, setFormData] = useState({ name: '', url: '', email: '' });
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: '' }));
    }
  };

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.name.trim()) {
      newErrors.name = 'Server name is required';
    } else if (formData.name.length < 2) {
      newErrors.name = 'Name must be at least 2 characters';
    }

    if (!formData.url.trim()) {
      newErrors.url = 'URL is required';
    } else if (!formData.url.startsWith('http://') && !formData.url.startsWith('https://')) {
      newErrors.url = 'URL must start with http:// or https://';
    }

    if (!formData.email.trim()) {
      newErrors.email = 'Email is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'Invalid email format';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    setLoading(true);
    try {
      await onSubmit(formData);
      setFormData({ name: '', url: '', email: '' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Server Name Input */}
        <div className="relative">
          <label htmlFor="name" className="block text-xs font-semibold text-slate-300 mb-2 uppercase tracking-wider">
            Server Name
          </label>
          <input
            type="text"
            id="name"
            name="name"
            value={formData.name}
            onChange={handleChange}
            placeholder="e.g., My Website"
            className={`w-full px-4 py-3 bg-white/10 border rounded-xl focus:ring-2 focus:ring-cyan-400 focus:border-cyan-400 focus:bg-white/15 transition-all text-white placeholder-slate-400 ${
              errors.name ? 'border-red-500/50 focus:border-red-500 focus:ring-red-400' : 'border-white/20'
            }`}
          />
          {errors.name && <p className="text-red-400 text-xs mt-2 font-medium">{errors.name}</p>}
        </div>

        {/* URL Input */}
        <div className="relative">
          <label htmlFor="url" className="block text-xs font-semibold text-slate-300 mb-2 uppercase tracking-wider">
            Server URL
          </label>
          <input
            type="url"
            id="url"
            name="url"
            value={formData.url}
            onChange={handleChange}
            placeholder="https://example.com"
            className={`w-full px-4 py-3 bg-white/10 border rounded-xl focus:ring-2 focus:ring-cyan-400 focus:border-cyan-400 focus:bg-white/15 transition-all text-white placeholder-slate-400 ${
              errors.url ? 'border-red-500/50 focus:border-red-500 focus:ring-red-400' : 'border-white/20'
            }`}
          />
          {errors.url && <p className="text-red-400 text-xs mt-2 font-medium">{errors.url}</p>}
        </div>

        {/* Email Input */}
        <div className="relative">
          <label htmlFor="email" className="block text-xs font-semibold text-slate-300 mb-2 uppercase tracking-wider">
            Alert Email
          </label>
          <input
            type="email"
            id="email"
            name="email"
            value={formData.email}
            onChange={handleChange}
            placeholder="your.email@example.com"
            className={`w-full px-4 py-3 bg-white/10 border rounded-xl focus:ring-2 focus:ring-cyan-400 focus:border-cyan-400 focus:bg-white/15 transition-all text-white placeholder-slate-400 ${
              errors.email ? 'border-red-500/50 focus:border-red-500 focus:ring-red-400' : 'border-white/20'
            }`}
          />
          {errors.email && <p className="text-red-400 text-xs mt-2 font-medium">{errors.email}</p>}
        </div>
      </div>

      <button
        type="submit"
        disabled={loading}
        className="mt-6 px-8 py-3 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-semibold rounded-xl shadow-lg shadow-cyan-500/20 hover:shadow-cyan-500/40 transform hover:scale-105 transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:scale-100 flex items-center justify-center gap-2"
      >
        {loading ? (
          <>
            <span className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
            <span>Adding Server...</span>
          </>
        ) : (
          <>
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            <span>Add Server</span>
          </>
        )}
      </button>
    </form>
  );
}

