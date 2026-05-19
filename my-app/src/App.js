import React, { useRef, useState } from "react";
import { BrowserRouter as Router, Routes, Route, useNavigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { WizardProvider } from "./context/WizardContext";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { LoginPage } from "./pages/LoginPage";
import Dashboard from "./pages/Dashboard";

function DashboardLayout() {
  const { logout, user } = useAuth();

  return (
    <div style={{ minHeight: '100vh', background: '#f0efe8' }}>
      {/* App nav bar */}
      <div style={{
        position: 'fixed',
        top: '32px',
        left: 0,
        right: 0,
        height: '52px',
        background: '#f0efe8',
        borderBottom: '1px solid #e4e3dc',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 56px',
        zIndex: 1000,
        boxSizing: 'border-box',
      }}>
        <span style={{ fontSize: '0.9em', fontWeight: '500', color: '#1e1e1e', letterSpacing: '-0.2px' }}>
          LabHub
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <span style={{ fontSize: '0.85em', color: '#888' }}>{user?.username}</span>
          <button
            onClick={logout}
            style={{
              padding: '6px 14px',
              background: 'transparent',
              color: '#888',
              border: '1px solid #d4d3cc',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '0.82em',
              fontWeight: '500',
              transition: 'border-color 0.15s, color 0.15s',
            }}
            onMouseOver={(e) => { e.target.style.borderColor = '#999'; e.target.style.color = '#444'; }}
            onMouseOut={(e) => { e.target.style.borderColor = '#d4d3cc'; e.target.style.color = '#888'; }}
          >
            Sign out
          </button>
        </div>
      </div>
      {/* Push content below both bars */}
      <div style={{ paddingTop: '84px' }}>
        <Dashboard />
      </div>
    </div>
  );
}

function NewPipeline() {
  const { token } = useAuth();
  const [formData, setFormData] = useState({
    binfile: null,
    samplingRate: 30000.0,
    numberOfChannels: 64,
    gainToUV: 0.1949999928,
    offsetToUV: 0.0,
    probe: null,
    removeChannels: [],
    badChannels: []
  });
  const [resultJSON, setResultJSON] = useState("");

  const handleInputChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleChannelToggle = (field, channelNum) => {
    setFormData(prev => ({
      ...prev,
      [field]: prev[field].includes(channelNum)
        ? prev[field].filter(ch => ch !== channelNum)
        : [...prev[field], channelNum]
    }));
  };

  const handleSubmit = async () => {
    try {
      // Basic validation
      if (!formData.binfile) return alert('Please select a bin file to upload');

      const fd = new FormData();
      // Field names match Django model: bin_file, probe_file
      fd.append('bin_file', formData.binfile);
      if (formData.probe) fd.append('probe_file', formData.probe);
      fd.append('sampling_rate', String(formData.samplingRate));
      fd.append('num_channels', String(formData.numberOfChannels));
      fd.append('gain_to_uV', String(formData.gainToUV));
      fd.append('offset_to_uV', String(formData.offsetToUV));
      // JSON-encode arrays so DRF JSONField can parse them
      fd.append('remove_channels', JSON.stringify(formData.removeChannels.sort((a, b) => a - b)));
      fd.append('bad_channels', JSON.stringify(formData.badChannels.sort((a, b) => a - b)));

      const token = window.localStorage.getItem('token');

      // TODO: /pipeline-factory/recordings/ backend endpoint is not yet implemented.
      // Replace this URL once the recording registration endpoint exists.
      const API_BASE = `${window.location.origin}/pipeline-factory`;
      const resp = await fetch(`${API_BASE}/recordings/`, {
        method: 'POST',
        headers: token ? { 'Authorization': `Token ${token}` } : {},
        body: fd
      });
      const contentType = resp.headers.get('content-type') || '';
      let data;
      if (contentType.includes('application/json')) {
        data = await resp.json();
      } else {
        data = await resp.text();
      }

      if (!resp.ok) {
        const msg = typeof data === 'string' ? data : (data.detail || JSON.stringify(data));
        setResultJSON(typeof data === 'string' ? data : JSON.stringify(data, null, 2));
        return alert('Upload failed: ' + msg);
      }

      // Success: show server response (including step_config hash)
      setResultJSON(typeof data === 'string' ? data : JSON.stringify(data, null, 2));
      const stepHash = typeof data === 'string' ? 'see response' : (data.step_config || 'unknown');
      alert('Recording uploaded and linked to StepConfig: ' + stepHash);
    } catch (err) {
      // Better error reporting: log full error and show a helpful alert
      console.error('Recording upload error:', err);
      const msg = err && err.message ? err.message : String(err);
      try {
        // Some errors (DOMException) have name and message
        alert('Unexpected error: ' + msg + '\nSee console for details.');
      } catch (e) {
        alert('Unexpected error occurred. Check console for details.');
      }
      setResultJSON(JSON.stringify({ error: msg }, null, 2));
    }
  };

  const renderCheckboxGrid = (field, label) => {
    const channels = [];
    for (let i = 1; i <= formData.numberOfChannels; i++) {
      channels.push(
        <label key={i} style={{ display: 'flex', alignItems: 'center', margin: '5px' }}>
          <input
            type='checkbox'
            checked={formData[field].includes(i)}
            onChange={() => handleChannelToggle(field, i)}
            style={{ marginRight: '5px' }}
          />
          {i}
        </label>
      );
    }
    return (
      <div style={{ marginBottom: '20px' }}>
        <label style={{ display: 'block', marginBottom: '10px', fontWeight: 'bold' }}>
          {label}
        </label>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(60px, 1fr))',
          gap: '5px',
          maxHeight: '200px',
          overflowY: 'auto',
          border: '1px solid #ddd',
          padding: '10px',
          borderRadius: '4px'
        }}>
          {channels}
        </div>
        {formData[field].length > 0 && (
          <p style={{ marginTop: '10px', fontSize: '14px', color: '#666' }}>
            Selected: {formData[field].sort((a, b) => a - b).join(', ')}
          </p>
        )}
      </div>
    );
  };

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #1e3c72 0%, #2a5298 100%)',
      padding: '20px',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
    }}>
      <div style={{
        background: 'rgba(255, 255, 255, 0.95)',
        padding: '30px',
        borderRadius: '12px',
        width: '100%',
        maxWidth: '600px',
        boxShadow: '0 8px 32px rgba(0,0,0,0.2)'
      }}>
        <h2 style={{ textAlign: 'center', marginBottom: '30px', color: '#333' }}>
          Create Recording
        </h2>
        <div style={{ display: 'grid', gap: '20px' }}>
          {/* Binfile */}
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
              Binfile:
            </label>
            <input
              type='file'
              onChange={(e) => handleInputChange('binfile', e.target.files[0] || null)}
              style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
            />
          </div>
          {/* Sampling Rate */}
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
              Sampling Rate:
            </label>
            <input
              type='number'
              value={formData.samplingRate}
              onChange={(e) => handleInputChange('samplingRate', parseFloat(e.target.value))}
              style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
            />
          </div>
          {/* Number of Channels */}
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
              Number of Channels:
            </label>
            <input
              type='number'
              value={formData.numberOfChannels}
              onChange={(e) => handleInputChange('numberOfChannels', parseInt(e.target.value))}
              style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
            />
          </div>
          {/* Gain to uV */}
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
              Gain to uV:
            </label>
            <input
              type='number'
              step='any'
              value={formData.gainToUV}
              onChange={(e) => handleInputChange('gainToUV', parseFloat(e.target.value))}
              style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
            />
          </div>
          {/* Offset to uV */}
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
              Offset to uV:
            </label>
            <input
              type='number'
              step='any'
              value={formData.offsetToUV}
              onChange={(e) => handleInputChange('offsetToUV', parseFloat(e.target.value))}
              style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
            />
          </div>
          {/* Probe */}
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
              Probe:
            </label>
            <input
              type='file'
              onChange={(e) => handleInputChange('probe', e.target.files[0] || null)}
              style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
            />
          </div>
          {/* Remove Channels Grid */}
          {formData.numberOfChannels > 0 && renderCheckboxGrid('removeChannels', 'Remove Channels')}
          {/* Bad Channels Grid */}
          {formData.numberOfChannels > 0 && renderCheckboxGrid('badChannels', 'Bad Channels')}
          {/* Submit Button */}
          <button
            onClick={handleSubmit}
            style={{
              padding: '15px 30px',
              fontSize: '16px',
              borderRadius: '8px',
              border: 'none',
              background: '#4fc3f7',
              color: '#fff',
              cursor: 'pointer',
              boxShadow: '0 4px 14px rgba(0,0,0,0.15)',
              marginTop: '20px'
            }}
          >
            Submit
          </button>
          {/* JSON Result */}
          {resultJSON && (
            <div style={{ marginTop: '20px' }}>
              <h3 style={{ marginBottom: '10px' }}>Server response:</h3>
              <pre style={{
                background: '#f5f5f5',
                padding: '15px',
                borderRadius: '4px',
                overflow: 'auto',
                fontSize: '12px',
                border: '1px solid #ddd'
              }}>
                <code>{resultJSON}</code>
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function SubmitPipeline() {
  const { token } = useAuth();
  const [fileName, setFileName] = useState("");
  const [fileObj, setFileObj] = useState(null);
  const [description, setDescription] = useState("");
  const [serverResp, setServerResp] = useState("");
  const fileInputRef = useRef();

  const handleFileChange = (e) => {
    if (e.target.files.length > 0) {
      setFileName(e.target.files[0].name);
      setFileObj(e.target.files[0]);
    } else {
      setFileName("");
      setFileObj(null);
    }
  };

  const handleSubmit = async () => {
    if (!fileObj) {
      alert('Please select a JSON file first!');
      return;
    }
    if (!description.trim()) {
      alert('Please enter a description for the pipeline!');
      return;
    }

    try {
      const text = await fileObj.text();
      let parsed;
      try {
        parsed = JSON.parse(text);
      } catch (err) {
        alert('Selected file is not valid JSON');
        return;
      }

      // Normalize the uploaded JSON into the backend-expected shape:
      // The backend expects { description, steps: [ { config_block: {...} } ] }
      // Support three shapes:
      // 1) { steps: [ ... ] } (already correct)
      // 2) [ ... ] (an array of steps)
      // 3) the 'Json part 2' style: { job_steps: [ {identifier,...}, ... ], '<id>': { ... } }
      let stepsArray;
      if (Array.isArray(parsed)) {
        stepsArray = parsed;
      } else if (parsed.steps && Array.isArray(parsed.steps)) {
        stepsArray = parsed.steps;
      } else if (parsed.job_steps && Array.isArray(parsed.job_steps)) {
        // Build steps in the order listed in job_steps. For each entry, merge
        // any detailed config found at parsed[identifier] into the config_block.
        stepsArray = parsed.job_steps.map((js) => {
          const identifier = js.identifier || js.id || null;
          // Base block contains the minimal metadata from the job_steps entry
          const baseBlock = {
            function: js.function,
            identifier: identifier,
            depends: js.depends || [],
          };
          // Merge keyed config if present (e.g., parsed[identifier])
          let keyed = {};
          if (identifier && parsed[identifier] && typeof parsed[identifier] === 'object') {
            keyed = parsed[identifier];
          }
          // Final config block: keyed fields win (they contain params/details)
          const config_block = { ...baseBlock, ...keyed };
          return { config_block };
        });
      } else {
        // Fallback: try to use parsed as steps directly
        stepsArray = parsed.steps || parsed;
      }

      const payload = { description, steps: stepsArray };

      const token = window.localStorage.getItem('token');

      const API_BASE = 'http://localhost:8000/pipeline-factory';
      const resp = await fetch(`${API_BASE}/pipelines/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Token ${token}` } : {})
        },
        body: JSON.stringify(payload)
      });
      const contentType = resp.headers.get('content-type') || '';
      let data;
      if (contentType.includes('application/json')) {
        data = await resp.json();
      } else {
        data = await resp.text();
      }

      if (!resp.ok) {
        setServerResp(typeof data === 'string' ? data : JSON.stringify(data, null, 2));
        return alert('Pipeline submission failed: ' + (typeof data === 'string' ? data : (data.detail || JSON.stringify(data))));
      }

      setServerResp(typeof data === 'string' ? data : JSON.stringify(data, null, 2));
      alert('Pipeline submitted — pipeline_id: ' + (typeof data === 'string' ? 'see response' : (data.pipeline_id || 'unknown')));
    } catch (err) {
      console.error('Pipeline submit error:', err);
      const msg = err && err.message ? err.message : String(err);
      alert('Unexpected error: ' + msg + '\nSee console for details.');
      setServerResp(JSON.stringify({ error: msg }, null, 2));
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #1e3c72 0%, #2a5298 100%)',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px'
    }}>
      <div style={{
        background: 'rgba(255, 255, 255, 0.95)',
        padding: '30px',
        borderRadius: '12px',
        width: '100%',
        maxWidth: '500px',
        boxShadow: '0 8px 32px rgba(0,0,0,0.2)'
      }}>
        <h2 style={{
          textAlign: 'center',
          marginBottom: '30px',
          color: '#333'
        }}>
          Submit a Pipeline
        </h2>

        {/* Description Field */}
        <div style={{ marginBottom: '20px' }}>
          <label style={{
            display: 'block',
            marginBottom: '8px',
            fontWeight: 'bold',
            color: '#333'
          }}>
            Description of Pipeline: <span style={{ color: 'red' }}>*</span>
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder='Enter a description for your pipeline...'
            required
            style={{
              width: '100%',
              padding: '12px',
              borderRadius: '4px',
              border: '1px solid #ccc',
              fontSize: '14px',
              minHeight: '80px',
              resize: 'vertical',
              fontFamily: 'inherit'
            }}
          />
        </div>

        {/* File Upload */}
        <div style={{ marginBottom: '20px' }}>
          <label style={{
            display: 'block',
            marginBottom: '8px',
            fontWeight: 'bold',
            color: '#333'
          }}>
            JSON File: <span style={{ color: 'red' }}>*</span>
          </label>
          <input
            type='file'
            accept='.json,application/json'
            ref={fileInputRef}
            style={{ display: 'none' }}
            onChange={handleFileChange}
          />
          <button
            style={{
              padding: '12px 24px',
              fontSize: '16px',
              borderRadius: '6px',
              border: '1px solid #4fc3f7',
              background: '#4fc3f7',
              color: '#fff',
              cursor: 'pointer',
              width: '100%',
              marginBottom: '10px'
            }}
            onClick={() => fileInputRef.current.click()}
          >
            Select JSON File
          </button>
          {fileName && (
            <div style={{
              color: '#666',
              fontSize: '14px',
              padding: '8px',
              background: '#f0f8ff',
              borderRadius: '4px',
              border: '1px solid #e0e0e0'
            }}>
              Selected file: <strong>{fileName}</strong>
            </div>
          )}
        </div>

        {/* Submit Button */}
        <button
          style={{
            padding: '15px 30px',
            fontSize: '18px',
            borderRadius: '8px',
            border: 'none',
            background: '#81c784',
            color: '#fff',
            cursor: 'pointer',
            boxShadow: '0 4px 14px rgba(0,0,0,0.15)',
            width: '100%',
            marginTop: '10px'
          }}
          onClick={handleSubmit}
        >
          Submit Pipeline
        </button>

        {serverResp && (
          <div style={{ marginTop: '20px' }}>
            <h3 style={{ marginBottom: '10px' }}>Server response:</h3>
            <pre style={{
              background: '#f5f5f5',
              padding: '15px',
              borderRadius: '4px',
              overflow: 'auto',
              fontSize: '12px',
              border: '1px solid #ddd'
            }}>
              <code>{serverResp}</code>
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
function App() {
  return (
    <AuthProvider>
      <WizardProvider>
        <Router>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/dashboard" element={<ProtectedRoute><DashboardLayout /></ProtectedRoute>} />
            <Route path="/" element={<ProtectedRoute><DashboardLayout /></ProtectedRoute>} />
            <Route path="/new-pipeline" element={<ProtectedRoute><NewPipeline /></ProtectedRoute>} />
            <Route path="/submit-pipeline" element={<ProtectedRoute><SubmitPipeline /></ProtectedRoute>} />
          </Routes>
        </Router>
      </WizardProvider>
    </AuthProvider>
  );
}

export default App;