import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuthStore } from "../store/auth";
import { useLanguage } from "../store/language";
import NotificationBell from "./NotificationBell";
import AuditIntegrityModal from "./AuditIntegrityModal";
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
  ClipboardCheck,
  Scale,
  Languages,
} from "lucide-react";

export default function Navbar() {
  const { user, logout } = useAuthStore();
  const { lang, changeLanguage, t } = useLanguage();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [showAuditModal, setShowAuditModal] = useState(false);

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
                {t("sharedLabs")}
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
              {t("discoverEquipment")}
            </Link>

            <Link
              to="/fairness-simulator"
              className="flex items-center gap-1.5 text-gray-600 hover:text-brand-600 transition"
            >
              <Scale className="w-4 h-4 text-amber-600" />
              {t("fairnessSimulator")}
            </Link>

            {isOwnerOrManager && (
              <Link
                to="/owner/resources"
                className="flex items-center gap-1.5 text-gray-600 hover:text-brand-600 transition"
              >
                <Layers className="w-4 h-4" />
                {t("labInventory")}
              </Link>
            )}

            {isOwnerOrManager && (
              <Link
                to="/manager/review-queue"
                className="flex items-center gap-1.5 text-gray-600 hover:text-brand-600 transition"
              >
                <ClipboardCheck className="w-4 h-4" />
                {t("reviewQueue")}
              </Link>
            )}

            {isOwnerOrManager && (
              <button
                type="button"
                onClick={() => setShowAuditModal(true)}
                className="flex items-center gap-1.5 px-3 py-1 text-xs font-bold bg-purple-50 hover:bg-purple-100 text-purple-700 border border-purple-200 rounded-xl transition shadow-2xs"
                title="Verify SHA-256 Hash Chain Integrity"
              >
                <ShieldCheck className="w-3.5 h-3.5" />
                {t("verifyAudit")}
              </button>
            )}

            {isOwnerOrManager && (
              <Link
                to="/owner/resources/new"
                className="flex items-center gap-1.5 text-brand-600 hover:text-brand-700 font-semibold"
              >
                <PlusCircle className="w-4 h-4" />
                {t("listResource")}
              </Link>
            )}

            {/* Language Switcher Pill */}
            <div className="flex items-center bg-gray-100 p-0.5 rounded-xl border border-gray-200 text-[11px] font-bold">
              <button
                onClick={() => changeLanguage("en")}
                className={`px-2 py-0.5 rounded-lg transition ${
                  lang === "en" ? "bg-white text-gray-900 shadow-2xs" : "text-gray-500 hover:text-gray-900"
                }`}
                aria-label="Switch language to English"
              >
                EN
              </button>
              <button
                onClick={() => changeLanguage("mr")}
                className={`px-2 py-0.5 rounded-lg transition ${
                  lang === "mr" ? "bg-white text-gray-900 shadow-2xs" : "text-gray-500 hover:text-gray-900"
                }`}
                aria-label="मराठी भाषेवर स्विच करा"
              >
                मराठी
              </button>
              <button
                onClick={() => changeLanguage("hi")}
                className={`px-2 py-0.5 rounded-lg transition ${
                  lang === "hi" ? "bg-white text-gray-900 shadow-2xs" : "text-gray-500 hover:text-gray-900"
                }`}
                aria-label="हिंदी भाषा पर स्विच करें"
              >
                हिंदी
              </button>
            </div>

            {user ? (
              <div className="flex items-center gap-3 pl-3 border-l border-gray-200">
                <NotificationBell />

                <Link
                  to="/dashboard"
                  className="flex items-center gap-1.5 text-gray-700 hover:text-brand-600 font-semibold"
                >
                  <LayoutDashboard className="w-4 h-4" />
                  {t("dashboard")}
                </Link>

                <div className="flex items-center gap-1 text-xs font-semibold bg-amber-50 text-amber-700 px-2.5 py-1 rounded-full border border-amber-200">
                  <Coins className="w-3.5 h-3.5 text-amber-600" />
                  <span>{user.credit_balance} {t("welcomeCredits")}</span>
                </div>

                <div className="text-xs bg-gray-100 text-gray-700 px-2.5 py-1 rounded-full font-medium uppercase tracking-wide">
                  {user.role}
                </div>

                <button
                  onClick={handleLogout}
                  title={t("signOut")}
                  className="p-1.5 text-gray-400 hover:text-red-600 rounded-lg hover:bg-gray-100 transition"
                  aria-label="Sign out"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-3 pl-3 border-l border-gray-200">
                <Link
                  to="/login"
                  className="text-gray-700 hover:text-brand-600 font-semibold px-3 py-1.5"
                >
                  {t("signIn")}
                </Link>
                <Link
                  to="/register"
                  className="bg-brand-600 text-white px-4 py-2 rounded-xl text-sm font-semibold hover:bg-brand-700 transition shadow-sm shadow-brand-500/20"
                >
                  {t("register")}
                </Link>
              </div>
            )}
          </div>

          {/* Mobile action bar */}
          <div className="flex md:hidden items-center gap-2">
            {user && <NotificationBell />}
            <button
              onClick={() => setMobileOpen(!mobileOpen)}
              className="p-2 rounded-lg text-gray-600 hover:bg-gray-100"
              aria-label="Toggle mobile menu"
            >
              {mobileOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileOpen && (
        <div className="md:hidden border-b border-gray-200 bg-white px-4 pt-2 pb-4 space-y-2 text-sm font-medium">
          {/* Mobile Language Selector */}
          <div className="flex items-center justify-between px-3 py-2 border-b border-gray-100 mb-2">
            <span className="text-xs text-gray-500 font-bold uppercase tracking-wider flex items-center gap-1.5">
              <Languages className="w-3.5 h-3.5 text-brand-600" />
              Language
            </span>
            <div className="flex bg-gray-100 rounded-xl p-0.5 border border-gray-200 text-xs font-bold">
              <button
                type="button"
                onClick={() => changeLanguage("en")}
                className={`px-2.5 py-1 rounded-lg transition ${
                  lang === "en" ? "bg-white text-gray-900 shadow-xs" : "text-gray-500"
                }`}
              >
                EN
              </button>
              <button
                type="button"
                onClick={() => changeLanguage("mr")}
                className={`px-2.5 py-1 rounded-lg transition ${
                  lang === "mr" ? "bg-white text-gray-900 shadow-xs" : "text-gray-500"
                }`}
              >
                मराठी
              </button>
              <button
                type="button"
                onClick={() => changeLanguage("hi")}
                className={`px-2.5 py-1 rounded-lg transition ${
                  lang === "hi" ? "bg-white text-gray-900 shadow-xs" : "text-gray-500"
                }`}
              >
                हिंदी
              </button>
            </div>
          </div>

          {/* Audit Integrity Button in Mobile Drawer for Managers/Admins */}
          {isOwnerOrManager && (
            <button
              type="button"
              onClick={() => {
                setMobileOpen(false);
                setShowAuditModal(true);
              }}
              className="w-full text-left flex items-center gap-2 px-3 py-2 rounded-xl text-emerald-800 bg-emerald-50 hover:bg-emerald-100 font-bold text-xs border border-emerald-200 mb-2 transition"
            >
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              {t("verifyAudit")}
            </button>
          )}
          <Link
            to="/equipment"
            onClick={() => setMobileOpen(false)}
            className="block px-3 py-2 rounded-lg text-gray-700 hover:bg-gray-50"
          >
            Discover Equipment
          </Link>
          <Link
            to="/fairness-simulator"
            onClick={() => setMobileOpen(false)}
            className="block px-3 py-2 rounded-lg text-amber-700 hover:bg-amber-50 font-bold"
          >
            Fairness Simulator
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
                to="/manager/review-queue"
                onClick={() => setMobileOpen(false)}
                className="block px-3 py-2 rounded-lg text-gray-700 hover:bg-gray-50 font-semibold"
              >
                Review Queue
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

      {/* Cryptographic Audit Integrity Verification Modal */}
      <AuditIntegrityModal
        isOpen={showAuditModal}
        onClose={() => setShowAuditModal(false)}
      />
    </nav>
  );
}

