import { BrowserRouter, Routes, Route, Navigate, Link } from "react-router-dom";
import { useEffect, useState } from "react";
import { useAuthStore } from "./store/auth";
import api from "./api/client";

// ── Pages (inline for scaffold; extract to pages/ as app grows) ──────────────

function Home() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-br from-brand-50 to-blue-100">
      <div className="text-center max-w-2xl px-4">
        <h1 className="text-5xl font-extrabold text-brand-700 mb-4">OpenBench</h1>
        <p className="text-xl text-gray-600 mb-2">
          <em>"Every bench, every hour — earning for science."</em>
        </p>
        <p className="text-gray-500 mb-8">
          A trusted, credit-based platform connecting underused college labs with MSMEs,
          ITI students, and startups.
        </p>
        <div className="flex gap-4 justify-center">
          <Link
            to="/equipment"
            className="bg-brand-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-brand-700 transition"
          >
            Browse Equipment
          </Link>
          <Link
            to="/login"
            className="border border-brand-600 text-brand-600 px-6 py-3 rounded-lg font-semibold hover:bg-brand-50 transition"
          >
            Sign In
          </Link>
        </div>
      </div>
    </div>
  );
}

function Login() {
  const { setAuth, user } = useAuthStore();
  if (user) return <Navigate to="/dashboard" />;

  const handleSubmit = async (e) => {
    e.preventDefault();
    const form = new FormData(e.target);
    try {
      const { data: tokens } = await api.post(
        "/auth/login",
        new URLSearchParams({ username: form.get("email"), password: form.get("password") }),
        { headers: { "Content-Type": "application/x-www-form-urlencoded" } }
      );
      const { data: me } = await api.get("/auth/me", {
        headers: { Authorization: `Bearer ${tokens.access_token}` },
      });
      setAuth(me, tokens.access_token, tokens.refresh_token);
      window.location.href = "/dashboard";
    } catch {
      alert("Invalid credentials.");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white shadow rounded-xl p-8 w-full max-w-md">
        <h2 className="text-2xl font-bold mb-6 text-brand-700">Sign in to OpenBench</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <input name="email" type="email" placeholder="Email" required
            className="w-full border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-brand-400" />
          <input name="password" type="password" placeholder="Password" required
            className="w-full border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-brand-400" />
          <button type="submit"
            className="w-full bg-brand-600 text-white py-2 rounded-lg font-semibold hover:bg-brand-700 transition">
            Sign In
          </button>
        </form>
        <p className="mt-4 text-sm text-gray-500 text-center">
          No account? <Link to="/register" className="text-brand-600 font-medium">Register</Link>
        </p>
      </div>
    </div>
  );
}

function Register() {
  const handleSubmit = async (e) => {
    e.preventDefault();
    const form = new FormData(e.target);
    try {
      await api.post("/auth/register", {
        email: form.get("email"),
        full_name: form.get("full_name"),
        password: form.get("password"),
        organisation: form.get("organisation"),
      });
      alert("Registered! You get 50 welcome credits. Please sign in.");
      window.location.href = "/login";
    } catch (err) {
      alert(err.response?.data?.detail || "Registration failed.");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white shadow rounded-xl p-8 w-full max-w-md">
        <h2 className="text-2xl font-bold mb-6 text-brand-700">Create Account</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <input name="full_name" type="text" placeholder="Full Name" required
            className="w-full border rounded-lg px-4 py-2" />
          <input name="email" type="email" placeholder="Email" required
            className="w-full border rounded-lg px-4 py-2" />
          <input name="password" type="password" placeholder="Password" required
            className="w-full border rounded-lg px-4 py-2" />
          <input name="organisation" type="text" placeholder="Organisation (optional)"
            className="w-full border rounded-lg px-4 py-2" />
          <button type="submit"
            className="w-full bg-brand-600 text-white py-2 rounded-lg font-semibold hover:bg-brand-700">
            Register
          </button>
        </form>
      </div>
    </div>
  );
}

function Equipment() {
  const [items, setItems] = useState([]);
  useEffect(() => {
    api.get("/equipment").then(r => setItems(r.data)).catch(() => {});
  }, []);

  return (
    <div className="max-w-5xl mx-auto px-4 py-10">
      <h2 className="text-3xl font-bold text-brand-700 mb-6">Available Equipment & Spaces</h2>
      {items.length === 0 && <p className="text-gray-500">No equipment found. Seed demo data first.</p>}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {items.map(eq => (
          <div key={eq.id} className="bg-white rounded-xl shadow p-5 border border-gray-100">
            <span className="text-xs uppercase font-semibold text-brand-600 bg-brand-50 px-2 py-0.5 rounded">
              {eq.type}
            </span>
            <h3 className="font-bold text-lg mt-2 text-gray-800">{eq.name}</h3>
            <p className="text-sm text-gray-500 mt-1">{eq.lab_name}</p>
            <p className="text-sm text-gray-600 mt-2 line-clamp-2">{eq.description}</p>
            <div className="mt-3 flex items-center justify-between">
              <span className="font-bold text-brand-700">{eq.credit_per_hour} cr / hr</span>
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium
                ${eq.status === 'available' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                {eq.status}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function Dashboard() {
  const { user, logout } = useAuthStore();
  const [bookings, setBookings] = useState([]);
  const [balance, setBalance] = useState(null);

  useEffect(() => {
    if (!user) return;
    api.get("/bookings").then(r => setBookings(r.data)).catch(() => {});
    api.get("/credits/balance").then(r => setBalance(r.data)).catch(() => {});
  }, [user]);

  if (!user) return <Navigate to="/login" />;

  return (
    <div className="max-w-4xl mx-auto px-4 py-10">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-brand-700">Welcome, {user.full_name}</h2>
          <p className="text-gray-500 text-sm">{user.role} · {user.organisation}</p>
        </div>
        <div className="flex items-center gap-4">
          {balance && (
            <div className="text-right">
              <p className="text-sm text-gray-500">Spendable Credits</p>
              <p className="text-2xl font-bold text-brand-700">{balance.spendable}</p>
            </div>
          )}
          <button onClick={logout}
            className="text-sm text-red-500 hover:text-red-700 font-medium">
            Sign Out
          </button>
        </div>
      </div>

      <h3 className="font-semibold text-lg mb-3 text-gray-700">My Bookings</h3>
      {bookings.length === 0 && (
        <p className="text-gray-500">No bookings yet. <Link to="/equipment" className="text-brand-600 font-medium">Browse equipment →</Link></p>
      )}
      <div className="space-y-3">
        {bookings.map(b => (
          <div key={b.id} className="bg-white border rounded-xl p-4 flex items-center justify-between">
            <div>
              <p className="font-medium text-gray-800">Booking #{b.id} · Equipment #{b.equipment_id}</p>
              <p className="text-sm text-gray-500">
                {new Date(b.slot_start).toLocaleString()} — {new Date(b.slot_end).toLocaleString()}
              </p>
            </div>
            <span className={`text-xs font-semibold px-3 py-1 rounded-full
              ${b.status === 'COMPLETED' ? 'bg-green-100 text-green-700' :
                b.status === 'APPROVED' ? 'bg-blue-100 text-blue-700' :
                b.status === 'PENDING' ? 'bg-yellow-100 text-yellow-700' :
                'bg-red-100 text-red-700'}`}>
              {b.status}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function Navbar() {
  const { user } = useAuthStore();
  return (
    <nav className="bg-white shadow-sm border-b">
      <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
        <Link to="/" className="font-extrabold text-xl text-brand-700">OpenBench</Link>
        <div className="flex gap-5 text-sm font-medium">
          <Link to="/equipment" className="text-gray-600 hover:text-brand-600">Equipment</Link>
          {user ? (
            <Link to="/dashboard" className="text-brand-600">Dashboard</Link>
          ) : (
            <>
              <Link to="/login" className="text-gray-600 hover:text-brand-600">Sign In</Link>
              <Link to="/register" className="bg-brand-600 text-white px-3 py-1 rounded-lg hover:bg-brand-700">Register</Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}

// ── App ───────────────────────────────────────────────────────────────────────

export default function App() {
  const { setAuth } = useAuthStore();

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (token) {
      api.get("/auth/me").then(r => {
        // Re-hydrate user from API
        useAuthStore.setState({ user: r.data });
      }).catch(() => {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
      });
    }
  }, []);

  return (
    <BrowserRouter>
      <Navbar />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/equipment" element={<Equipment />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </BrowserRouter>
  );
}
