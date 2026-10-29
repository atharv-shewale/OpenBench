import { BrowserRouter, Routes, Route, Navigate, Link } from "react-router-dom";
import { useEffect, useState } from "react";
import { useAuthStore } from "./store/auth";
import api from "./api/client";
import Navbar from "./components/Navbar";

// Pages
import EquipmentDiscovery from "./pages/EquipmentDiscovery";
import EquipmentDetail from "./pages/EquipmentDetail";
import OwnerResourceList from "./pages/OwnerResourceList";
import ResourceEditor from "./pages/ResourceEditor";

function Home() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-br from-brand-50 via-white to-indigo-50/40">
      <div className="text-center max-w-3xl px-4 py-16">
        <span className="inline-block mb-3 px-3 py-1 bg-brand-50 border border-brand-200/80 text-brand-700 text-xs font-bold rounded-full uppercase tracking-wider">
          48-Hour Open Innovation Hackathon
        </span>
        <h1 className="text-5xl sm:text-6xl font-black text-gray-900 tracking-tight leading-tight mb-4">
          Open<span className="text-brand-600">Bench</span>
        </h1>
        <p className="text-xl text-gray-600 italic font-medium mb-4">
          "Every bench, every hour — earning for science."
        </p>
        <p className="text-gray-500 text-base max-w-xl mx-auto mb-8 leading-relaxed">
          Safely unlock underused college testing and fabrication labs for local MSMEs,
          ITI apprentices, and startups using a verified, credit-based booking platform.
        </p>
        <div className="flex flex-wrap gap-4 justify-center">
          <Link
            to="/equipment"
            className="bg-brand-600 text-white px-7 py-3.5 rounded-2xl font-bold hover:bg-brand-700 transition shadow-lg shadow-brand-500/25"
          >
            Explore Equipment & Spaces
          </Link>
          <Link
            to="/owner/resources"
            className="bg-white border border-gray-300 text-gray-700 px-7 py-3.5 rounded-2xl font-bold hover:bg-gray-50 transition shadow-2xs"
          >
            Lab Manager Portal
          </Link>
        </div>

        {/* Feature Highlights */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 mt-16 text-left">
          <div className="bg-white/80 backdrop-blur-xs p-5 rounded-2xl border border-gray-200/80 shadow-2xs">
            <div className="w-8 h-8 rounded-xl bg-blue-100 text-blue-700 font-bold flex items-center justify-center text-sm mb-3">
              1
            </div>
            <h4 className="font-bold text-gray-900 text-sm">Credit-Based Booking</h4>
            <p className="text-gray-500 text-xs mt-1">
              Guaranteed credit hold and transparent deduction upon session checkout.
            </p>
          </div>

          <div className="bg-white/80 backdrop-blur-xs p-5 rounded-2xl border border-gray-200/80 shadow-2xs">
            <div className="w-8 h-8 rounded-xl bg-purple-100 text-purple-700 font-bold flex items-center justify-center text-sm mb-3">
              2
            </div>
            <h4 className="font-bold text-gray-900 text-sm">Hash-Chained Audit</h4>
            <p className="text-gray-500 text-xs mt-1">
              Every creation, approval, and state transition writes to an append-only ledger.
            </p>
          </div>

          <div className="bg-white/80 backdrop-blur-xs p-5 rounded-2xl border border-gray-200/80 shadow-2xs">
            <div className="w-8 h-8 rounded-xl bg-emerald-100 text-emerald-700 font-bold flex items-center justify-center text-sm mb-3">
              3
            </div>
            <h4 className="font-bold text-gray-900 text-sm">Human Governance</h4>
            <p className="text-gray-500 text-xs mt-1">
              Automated actions are advisory only; no penalty without manager review.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function Login() {
  const { setAuth, user } = useAuthStore();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  if (user) return <Navigate to="/dashboard" />;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    const form = new FormData(e.target);
    try {
      const { data: tokens } = await api.post(
        "/auth/login",
        new URLSearchParams({
          username: form.get("email"),
          password: form.get("password"),
        }),
        { headers: { "Content-Type": "application/x-www-form-urlencoded" } }
      );
      const { data: me } = await api.get("/auth/me", {
        headers: { Authorization: `Bearer ${tokens.access_token}` },
      });
      setAuth(me, tokens.access_token, tokens.refresh_token);
      window.location.href = "/dashboard";
    } catch (err) {
      setError("Invalid email or password credentials.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="bg-white shadow-sm border border-gray-200 rounded-3xl p-8 w-full max-w-md">
        <h2 className="text-2xl font-black text-gray-900">Sign in to OpenBench</h2>
        <p className="text-xs text-gray-500 mt-1 mb-6">
          Access your credits, active lab bookings, and certifications.
        </p>

        {error && (
          <div className="mb-4 p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-xl font-medium">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4 text-sm">
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-gray-500 mb-1">
              Email
            </label>
            <input
              name="email"
              type="email"
              placeholder="e.g. rahul.mondal@iti-jadavpur.ac.in"
              required
              className="w-full bg-gray-50 border border-gray-300 rounded-xl px-4 py-2.5 text-xs focus:ring-2 focus:ring-brand-500 focus:bg-white"
            />
          </div>

          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-gray-500 mb-1">
              Password
            </label>
            <input
              name="password"
              type="password"
              placeholder="••••••••"
              required
              className="w-full bg-gray-50 border border-gray-300 rounded-xl px-4 py-2.5 text-xs focus:ring-2 focus:ring-brand-500 focus:bg-white"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-brand-600 text-white py-3 rounded-xl font-bold text-xs hover:bg-brand-700 transition shadow-sm shadow-brand-500/20"
          >
            {loading ? "Authenticating..." : "Sign In"}
          </button>
        </form>

        <div className="mt-6 pt-4 border-t border-gray-100 text-center">
          <p className="text-xs text-gray-500">
            Demo credentials: <code className="bg-gray-100 px-1 py-0.5 rounded">rahul.mondal@iti-jadavpur.ac.in</code> / <code className="bg-gray-100 px-1 py-0.5 rounded">User@123</code>
          </p>
          <p className="mt-3 text-xs text-gray-500">
            Don't have an account?{" "}
            <Link to="/register" className="text-brand-600 font-bold hover:underline">
              Register now (+50 credits)
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}

function Register() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    const form = new FormData(e.target);
    try {
      await api.post("/auth/register", {
        email: form.get("email"),
        full_name: form.get("full_name"),
        password: form.get("password"),
        organisation: form.get("organisation"),
      });
      alert("Registration successful! 50 welcome credits granted. Please sign in.");
      window.location.href = "/login";
    } catch (err) {
      setError(err.response?.data?.detail || "Registration failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="bg-white shadow-sm border border-gray-200 rounded-3xl p-8 w-full max-w-md">
        <h2 className="text-2xl font-black text-gray-900">Create Account</h2>
        <p className="text-xs text-gray-500 mt-1 mb-6">
          Receive 50 welcome credits upon registration to book lab equipment.
        </p>

        {error && (
          <div className="mb-4 p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-xl font-medium">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4 text-sm">
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-gray-500 mb-1">
              Full Name
            </label>
            <input
              name="full_name"
              type="text"
              placeholder="e.g. Rahul Mondal"
              required
              className="w-full bg-gray-50 border border-gray-300 rounded-xl px-4 py-2.5 text-xs focus:ring-2 focus:ring-brand-500"
            />
          </div>

          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-gray-500 mb-1">
              Email
            </label>
            <input
              name="email"
              type="email"
              placeholder="name@institution.ac.in"
              required
              className="w-full bg-gray-50 border border-gray-300 rounded-xl px-4 py-2.5 text-xs focus:ring-2 focus:ring-brand-500"
            />
          </div>

          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-gray-500 mb-1">
              Password
            </label>
            <input
              name="password"
              type="password"
              placeholder="••••••••"
              required
              className="w-full bg-gray-50 border border-gray-300 rounded-xl px-4 py-2.5 text-xs focus:ring-2 focus:ring-brand-500"
            />
          </div>

          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-gray-500 mb-1">
              Affiliated Organisation / College
            </label>
            <input
              name="organisation"
              type="text"
              placeholder="e.g. ITI Jadavpur or Startup name"
              className="w-full bg-gray-50 border border-gray-300 rounded-xl px-4 py-2.5 text-xs focus:ring-2 focus:ring-brand-500"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-brand-600 text-white py-3 rounded-xl font-bold text-xs hover:bg-brand-700 transition shadow-sm shadow-brand-500/20"
          >
            {loading ? "Creating..." : "Register & Claim 50 Credits"}
          </button>
        </form>
      </div>
    </div>
  );
}

function Dashboard() {
  const { user } = useAuthStore();
  const [bookings, setBookings] = useState([]);
  const [balance, setBalance] = useState(null);

  useEffect(() => {
    if (!user) return;
    api.get("/bookings").then((r) => setBookings(r.data)).catch(() => {});
    api.get("/credits/balance").then((r) => setBalance(r.data)).catch(() => {});
  }, [user]);

  if (!user) return <Navigate to="/login" />;

  return (
    <div className="min-h-screen bg-gray-50 py-10">
      <div className="max-w-5xl mx-auto px-4 sm:px-6">
        <div className="bg-white rounded-3xl border border-gray-200 p-8 shadow-sm mb-8">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-gray-100">
            <div>
              <h2 className="text-2xl font-black text-gray-900">
                Welcome, {user.full_name}
              </h2>
              <p className="text-xs text-gray-500 mt-1">
                {user.role.toUpperCase()} · {user.organisation || "Individual Member"}
              </p>
            </div>

            {balance && (
              <div className="bg-brand-50 border border-brand-100 px-5 py-3 rounded-2xl flex items-center gap-4">
                <div>
                  <span className="text-[11px] font-bold uppercase tracking-wider text-brand-600 block">
                    Spendable Credits
                  </span>
                  <span className="text-2xl font-black text-brand-700">
                    {balance.spendable}
                  </span>
                </div>
                {balance.credit_held > 0 && (
                  <div className="border-l border-brand-200 pl-4">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-gray-400 block">
                      Held in Slots
                    </span>
                    <span className="text-lg font-bold text-gray-600">
                      {balance.credit_held}
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="mt-8">
            <h3 className="font-bold text-gray-900 text-lg mb-4">My Lab Sessions</h3>
            {bookings.length === 0 ? (
              <div className="bg-gray-50 border border-gray-200 rounded-2xl p-8 text-center text-xs text-gray-500">
                No active bookings found.{" "}
                <Link to="/equipment" className="text-brand-600 font-bold hover:underline">
                  Browse equipment →
                </Link>
              </div>
            ) : (
              <div className="space-y-3">
                {bookings.map((b) => (
                  <div
                    key={b.id}
                    className="p-4 bg-gray-50 hover:bg-gray-100/80 transition border border-gray-200 rounded-2xl flex items-center justify-between"
                  >
                    <div>
                      <p className="font-bold text-xs text-gray-900">
                        Booking #{b.id} · Equipment #{b.equipment_id}
                      </p>
                      <p className="text-[11px] text-gray-500 mt-0.5">
                        {new Date(b.slot_start).toLocaleString()} to{" "}
                        {new Date(b.slot_end).toLocaleTimeString()}
                      </p>
                      {b.purpose && (
                        <p className="text-xs text-gray-600 italic mt-1">
                          "{b.purpose}"
                        </p>
                      )}
                    </div>
                    <span
                      className={`text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider ${
                        b.status === "COMPLETED"
                          ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                          : b.status === "APPROVED"
                          ? "bg-blue-50 text-blue-700 border border-blue-200"
                          : b.status === "PENDING"
                          ? "bg-amber-50 text-amber-700 border border-amber-200"
                          : "bg-rose-50 text-rose-700 border border-rose-200"
                      }`}
                    >
                      {b.status}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const { setAuth } = useAuthStore();

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (token) {
      api.get("/auth/me").then((r) => {
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
        <Route path="/equipment" element={<EquipmentDiscovery />} />
        <Route path="/equipment/:id" element={<EquipmentDetail />} />
        <Route path="/owner/resources" element={<OwnerResourceList />} />
        <Route path="/owner/resources/new" element={<ResourceEditor />} />
        <Route path="/owner/resources/:id/edit" element={<ResourceEditor />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </BrowserRouter>
  );
}
