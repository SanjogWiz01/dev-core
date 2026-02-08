import React, { useState } from 'react';
import { Send, Upload, BarChart3, Loader } from 'lucide-react';

export default function DataAnalysisAgent() {
  const [input, setInput] = useState('');
  const [data, setData] = useState('');
  const [results, setResults] = useState('');
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState([]);

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (event) => {
        setData(event.target.result);
        setMessages(prev => [...prev, {
          type: 'system',
          text: `✓ Loaded: ${file.name} (${file.size} bytes)`
        }]);
      };
      reader.readAsText(file);
    }
  };

  const analyzeData = async () => {
    if (!input.trim()) return;

    setMessages(prev => [...prev, { type: 'user', text: input }]);
    setLoading(true);

    try {
      const response = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model: 'claude-sonnet-4-5-20250929',
          max_tokens: 1000,
          messages: [
            {
              role: 'user',
              content: `You are a data analysis expert. Analyze the following data and answer this question: "${input}"\n\nData:\n${data || 'No data provided yet'}`
            }
          ]
        })
      });

      const result = await response.json();
      const analysisText = result.content[0]?.text || 'No analysis available';
      
      setMessages(prev => [...prev, { type: 'assistant', text: analysisText }]);
      setResults(analysisText);
    } catch (error) {
      setMessages(prev => [...prev, { type: 'error', text: 'Error analyzing data. Please try again.' }]);
    } finally {
      setLoading(false);
      setInput('');
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      analyzeData();
    }
  };

  return (
    <div className="flex flex-col h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Header */}
      <div className="bg-slate-800/50 border-b border-slate-700 p-4">
        <div className="flex items-center gap-3 max-w-6xl mx-auto">
          <BarChart3 className="w-6 h-6 text-blue-400" />
          <h1 className="text-2xl font-bold text-white">Data Analysis Agent</h1>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="max-w-6xl mx-auto space-y-4">
          {messages.length === 0 && (
            <div className="text-center py-12">
              <BarChart3 className="w-16 h-16 text-slate-600 mx-auto mb-4" />
              <p className="text-slate-400 text-lg">Upload data and ask questions to get started</p>
            </div>
          )}
          
          {messages.map((msg, idx) => (
            <div key={idx} className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-2xl rounded-lg p-4 ${
                msg.type === 'user' ? 'bg-blue-600 text-white' :
                msg.type === 'assistant' ? 'bg-slate-700 text-slate-100' :
                'bg-red-900/50 text-red-200'
              }`}>
                <p className="whitespace-pre-wrap text-sm">{msg.text}</p>
              </div>
            </div>
          ))}
          
          {loading && (
            <div className="flex justify-start">
              <div className="bg-slate-700 rounded-lg p-4 flex items-center gap-2">
                <Loader className="w-4 h-4 animate-spin text-blue-400" />
                <p className="text-slate-300">Analyzing...</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Input Area */}
      <div className="bg-slate-800/50 border-t border-slate-700 p-4">
        <div className="max-w-6xl mx-auto space-y-3">
          {/* File Upload */}
          <div className="flex gap-2">
            <label className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg cursor-pointer text-slate-200 transition">
              <Upload className="w-4 h-4" />
              <span className="text-sm">Upload Data</span>
              <input type="file" hidden onChange={handleFileUpload} accept=".txt,.csv,.json" />
            </label>
            {data && <span className="text-xs text-slate-400 py-2">✓ Data loaded</span>}
          </div>

          {/* Query Input */}
          <div className="flex gap-2">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask a question about your data... (Shift+Enter for new line)"
              className="flex-1 px-4 py-2 bg-slate-700 text-white rounded-lg border border-slate-600 focus:border-blue-500 focus:outline-none resize-none"
              rows="2"
            />
            <button
              onClick={analyzeData}
              disabled={loading || !input.trim()}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-600 text-white rounded-lg transition flex items-center gap-2"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}