import TopBar from './TopBar.jsx';
import Sidebar from './Sidebar.jsx';

export default function CyberShell({ children }) {
  return (
    <div className="h-screen flex flex-col bg-base bg-grid-texture bg-grid">
      <TopBar />
      <div className="flex flex-1 min-h-0">
        <Sidebar />
        <main className="flex-1 min-w-0 overflow-y-auto">
          <div className="max-w-[1400px] mx-auto p-5">{children}</div>
        </main>
      </div>
    </div>
  );
}
