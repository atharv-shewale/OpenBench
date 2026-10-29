import React from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuthStore } from "../store/auth";
import {
  Compass,
  LayoutDashboard,
  Layers,
  LogOut,
  PlusCircle,
  ShieldCheck,
  Coins,
  Menu,
  X,
} from "lucide-react";

export default function Navbar() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = React.useState(false);

  const isOwnerOrManager = user && ["owner", "manager", "admin"].includes(user.role);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <nav className="bg-white/90 backdrop-blur-md sticky top-0 z-50 border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16 items-center">
          {/* Logo & Brand */}
          <Link to="/" className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-brand-600 to-indigo-600 flex items-center justify-center text-white font-black text-xl shadow-md shadow-brand-500/20">
              O
            </div>
            <div>
              <span className="font-extrabold text-xl tracking-tight text-gray-900">
                Open<span className="text-brand-600">Bench</span>
              </span>
              <span className="hidden sm:inline-block ml-2 text-xs font-semibold px-2 py-0.5 bg-brand-50 text-brand-700 rounded-full border border-brand-100">
                Shared Labs
              </span>
            </div>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-6 text-sm font-medium">
            <Link
              to="/equipment"
              className="flex items-center gap-1.5 text-gray-600 hover:text-brand-600 transition"
            >
              <Compass className="w-4 h-4" />
              Discover Equipment
            </Link>

            {isOwnerOrManager && (
              <Link
                to="/owner/resources"
                className="flex items-center gap-1.5 text-gray-600 hover:text-brand-600 transition"
              >
                <Layers className="w-4 h-4" />
                Lab Inventory
              </Link>
            )}

            {isOwnerOrManager && (
              <Link
                to="/owner/resources/new"
                className="flex items-center gap-1.5 text-brand-600 hover:text-brand-700 font-semibold"
              >
                <PlusCircle className="w-4 h-4" />
                List Resource
              </Link>
            )}

            {user ? (
              <div className="flex items-center gap-4 pl-4 border-l border-gray-200">
                <Link
                  to="/dashboard"
                  className="flex items-center gap-1.5 text-gray-700 hover:text-brand-600 font-semibold"
                >
                  <LayoutDashboard className="w-4 h-4" />
                  Dashboard
                </Link>

                <div className="flex items-center gap-1 text-xs font-semibold bg-amber-50 text-amber-700 px-2.5 py-1 rounded-full border border-amber-200">
                  <Coins className="w-3.5 h-3.5 text-amber-600" />
                  <span>{user.credit_balance} cr</span>
                </div>

                <div className="text-xs bg-gray-100 text-gray-700 px-2.5 py-1 rounded-full font-medium uppercase tracking-wide">
                  {user.role}
                </div>

                <button
                  onClick={handleLogout}
                  title="Sign out"
                  className="p-1.5 text-gray-400 hover:text-red-600 rounded-lg hover:bg-gray-100 transition"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-3 pl-4 border-l border-gray-200">
                <Link
                  to="/login"
                  className="text-gray-700 hover:text-brand-600 font-semibold px-3 py-1.5"
                >
                  Sign In
                </Link>
                <Link
                  to="/register"
                  className="bg-brand-600 text-white px-4 py-2 rounded-xl text-sm font-semibold hover:bg-brand-700 transition shadow-sm shadow-brand-500/20"
                >
                  Get Started
                </Link>
              </div>
            )}
          </div>

          {/* Mobile hamburger menu */}
          <div className="flex md:hidden items-center">
            <button
              onClick={() => setMobileOpen(!mobileOpen)}
              className="p-2 rounded-lg text-gray-600 hover:bg-gray-100"
            >
              {mobileOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileOpen && (
        <div className="md:hidden border-b border-gray-200 bg-white px-4 pt-2 pb-4 space-y-2 text-sm font-medium">
          <Link
            to="/equipment"
            onClick={() => setMobileOpen(false)}
            className="block px-3 py-2 rounded-lg text-gray-700 hover:bg-gray-50"
          >
            Discover Equipment
          </Link>
          {isOwnerOrManager && (
            <>
              <Link
                to="/owner/resources"
                onClick={() => setMobileOpen(false)}
                className="block px-3 py-2 rounded-lg text-gray-700 hover:bg-gray-50"
              >
                Lab Inventory
              </Link>
              <Link
                to="/owner/resources/new"
                onClick={() => setMobileOpen(false)}
                className="block px-3 py-2 rounded-lg text-brand-600 font-semibold hover:bg-brand-50"
              >
                + List New Resource
              </Link>
            </>
          )}
          {user ? (
            <>
              <Link
                to="/dashboard"
                onClick={() => setMobileOpen(false)}
                className="block px-3 py-2 rounded-lg text-gray-700 hover:bg-gray-50 font-semibold"
              >
                Dashboard ({user.credit_balance} credits)
              </Link>
              <button
                onClick={() => {
                  setMobileOpen(false);
                  handleLogout();
                }}
                className="w-full text-left px-3 py-2 rounded-lg text-red-600 hover:bg-red-50 font-semibold"
              >
                Sign Out ({user.full_name})
              </button>
            </>
          ) : (
            <div className="pt-2 flex flex-col gap-2">
              <Link
                to="/login"
                onClick={() => setMobileOpen(false)}
                className="text-center py-2 rounded-lg border border-gray-300 font-semibold"
              >
                Sign In
              </Link>
              <Link
                to="/register"
                onClick={() => setMobileOpen(false)}
                className="text-center py-2 rounded-lg bg-brand-600 text-white font-semibold"
              >
                Register
              </Link>
            </div>
          )}
        </div>
      )}
    </nav>
  );
}

