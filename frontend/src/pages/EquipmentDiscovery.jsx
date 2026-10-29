import React, { useState, useEffect } from "react";
import { Link, useSearchParams } from "react-router-dom";
import api from "../api/client";
import { useAuthStore } from "../store/auth";
import {
  Search,
  Filter,
  MapPin,
  Clock,
  Sparkles,
  ArrowRight,
  ShieldAlert,
  Coins,
  CheckCircle2,
  SlidersHorizontal,
  X,
} from "lucide-react";

export default function EquipmentDiscovery() {
  const { user } = useAuthStore();
  const [searchParams, setSearchParams] = useSearchParams();

  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filter state
  const [search, setSearch] = useState(searchParams.get("search") || "");
  const [category, setCategory] = useState(searchParams.get("category") || "");
  const [city, setCity] = useState(searchParams.get("city") || "");
  const [maxCredits, setMaxCredits] = useState(searchParams.get("maxCredits") || "");
  const [availableOnly, setAvailableOnly] = useState(true);
  const [eligibleOnly, setEligibleOnly] = useState(false);

  // User eligibility map { equipment_id: boolean }
  const [eligibilityMap, setEligibilityMap] = useState({});

  const fetchEquipment = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {};
      if (search) params.search = search;
      if (category) params.category = category;
      if (city) params.city = city;
      if (maxCredits) params.max_credit_per_hour = maxCredits;
      params.available_only = availableOnly;

      const { data } = await api.get("/equipment", { params });
      setItems(data);

      // If user is logged in, asynchronously check eligibility for the displayed equipment
      if (user) {
        data.forEach(async (equip) => {
          try {
            const elRes = await api.get(`/equipment/${equip.id}/eligibility`);
            setEligibilityMap((prev) => ({
              ...prev,
              [equip.id]: elRes.data.is_eligible,
            }));
          } catch {
            // Ignore failure
          }
        });
      }
    } catch (err) {
      setError("Failed to load equipment list. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEquipment();
  }, [category, city, availableOnly]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    fetchEquipment();
  };

  const clearFilters = () => {
    setSearch("");
    setCategory("");
    setCity("");
    setMaxCredits("");
    setAvailableOnly(true);
    setEligibleOnly(false);
  };

  const filteredItems = items.filter((item) => {
    if (eligibleOnly && user) {
      return eligibilityMap[item.id] === true;
    }
    return true;
  });

  return (
    <div className="min-h-screen bg-gray-50 py-10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-extrabold text-gray-900 tracking-tight">
            Discover Lab Equipment & Spaces
          </h1>
          <p className="text-gray-500 mt-2 text-base max-w-2xl">
            Access industrial-grade testing instruments, CNC machines, 3D printers, and
            specialized lab benches shared by verified colleges.
          </p>
        </div>

        {/* Search & Filter Bar */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200/80 p-5 mb-8">
          <form onSubmit={handleSearchSubmit} className="space-y-4">
            <div className="flex flex-col md:flex-row gap-3">
              <div className="relative flex-1">
                <Search className="w-5 h-5 absolute left-3.5 top-3 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search by equipment name, tool type, institution, or specs..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="w-full pl-10 pr-4 py-2.5 bg-gray-50 border border-gray-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:bg-white transition"
                />
              </div>

              <div className="flex gap-2">
                <button
                  type="submit"
                  className="bg-brand-600 hover:bg-brand-700 text-white font-semibold px-6 py-2.5 rounded-xl text-sm transition shadow-sm shadow-brand-500/20"
                >
                  Search
                </button>
                {(search || category || city || maxCredits || eligibleOnly) && (
                  <button
                    type="button"
                    onClick={clearFilters}
                    className="flex items-center gap-1.5 px-4 py-2.5 text-gray-500 hover:text-gray-700 text-sm font-medium border border-gray-300 rounded-xl hover:bg-gray-50"
                  >
                    <X className="w-4 h-4" /> Reset
                  </button>
                )}
              </div>
            </div>

            {/* Quick Filter Pills */}
            <div className="flex flex-wrap items-center gap-3 pt-3 border-t border-gray-100 text-xs">
              <span className="font-semibold text-gray-400 uppercase tracking-wider flex items-center gap-1">
                <SlidersHorizontal className="w-3.5 h-3.5" /> Filters:
              </span>

              {/* Category selector */}
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="bg-gray-100/80 hover:bg-gray-200/70 border-0 rounded-lg px-3 py-1.5 font-medium text-gray-700 focus:ring-2 focus:ring-brand-500"
              >
                <option value="">All Categories</option>
                <option value="fabrication">Fabrication & Machining</option>
                <option value="testing">Testing & Metrology</option>
                <option value="space">Spaces & Benches</option>
                <option value="other">Specialized Tools</option>
              </select>

              {/* City selector */}
              <select
                value={city}
                onChange={(e) => setCity(e.target.value)}
                className="bg-gray-100/80 hover:bg-gray-200/70 border-0 rounded-lg px-3 py-1.5 font-medium text-gray-700 focus:ring-2 focus:ring-brand-500"
              >
                <option value="">All Locations</option>
                <option value="Kolkata">Kolkata</option>
                <option value="Pune">Pune</option>
                <option value="Bengaluru">Bengaluru</option>
              </select>

              {/* Max credits filter */}
              <input
                type="number"
                placeholder="Max cr/hr"
                value={maxCredits}
                onChange={(e) => setMaxCredits(e.target.value)}
                onBlur={fetchEquipment}
                className="w-24 bg-gray-100/80 hover:bg-gray-200/70 border-0 rounded-lg px-3 py-1.5 font-medium text-gray-700 text-xs"
              />

              {/* Available only toggle */}
              <label className="flex items-center gap-1.5 cursor-pointer bg-gray-100/80 hover:bg-gray-200/70 px-3 py-1.5 rounded-lg text-gray-700 select-none">
                <input
                  type="checkbox"
                  checked={availableOnly}
                  onChange={(e) => setAvailableOnly(e.target.checked)}
                  className="rounded text-brand-600 focus:ring-brand-500 w-3.5 h-3.5"
                />
                <span>Available Only</span>
              </label>

              {/* Eligible only toggle (requires user) */}
              {user && (
                <label className="flex items-center gap-1.5 cursor-pointer bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 px-3 py-1.5 rounded-lg text-emerald-800 font-semibold select-none transition">
                  <input
                    type="checkbox"
                    checked={eligibleOnly}
                    onChange={(e) => setEligibleOnly(e.target.checked)}
                    className="rounded text-emerald-600 focus:ring-emerald-500 w-3.5 h-3.5"
                  />
                  <span>Show only what I'm eligible for</span>
                </label>
              )}
            </div>
          </form>
        </div>

        {/* States: Loading */}
        {loading && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[1, 2, 3, 4, 5, 6].map((n) => (
              <div
                key={n}
                className="bg-white rounded-2xl border border-gray-200 p-6 space-y-4 animate-pulse shadow-sm"
              >
                <div className="h-4 bg-gray-200 rounded w-1/4"></div>
                <div className="h-6 bg-gray-200 rounded w-3/4"></div>
                <div className="h-4 bg-gray-100 rounded w-full"></div>
                <div className="h-4 bg-gray-100 rounded w-2/3"></div>
                <div className="h-10 bg-gray-100 rounded"></div>
              </div>
            ))}
          </div>
        )}

        {/* States: Error */}
        {!loading && error && (
          <div className="bg-red-50 border border-red-200 rounded-2xl p-8 text-center text-red-700">
            <p className="font-semibold text-lg">{error}</p>
            <button
              onClick={fetchEquipment}
              className="mt-4 px-4 py-2 bg-red-600 text-white rounded-xl text-sm font-semibold hover:bg-red-700"
            >
              Retry
            </button>
          </div>
        )}

        {/* States: Empty */}
        {!loading && !error && filteredItems.length === 0 && (
          <div className="bg-white rounded-2xl border border-gray-200 p-12 text-center shadow-sm">
            <div className="w-14 h-14 bg-gray-100 text-gray-400 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <Search className="w-7 h-7" />
            </div>
            <h3 className="text-lg font-bold text-gray-800">No resources found</h3>
            <p className="text-gray-500 text-sm mt-1 max-w-sm mx-auto">
              We couldn't find any equipment matching your criteria. Try loosening your
              search filters.
            </p>
            <button
              onClick={clearFilters}
              className="mt-4 inline-flex items-center gap-2 px-4 py-2 bg-brand-50 text-brand-700 font-semibold rounded-xl text-sm hover:bg-brand-100"
            >
              Clear all filters
            </button>
          </div>
        )}

        {/* Equipment Grid */}
        {!loading && !error && filteredItems.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredItems.map((eq) => {
              const isEligible = eligibilityMap[eq.id];

              return (
                <div
                  key={eq.id}
                  className="bg-white rounded-2xl border border-gray-200/80 shadow-sm hover:shadow-md transition flex flex-col justify-between overflow-hidden group"
                >
                  <div className="p-6">
                    {/* Header tags */}
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-xs uppercase tracking-wider font-bold text-brand-600 bg-brand-50 border border-brand-100 px-2.5 py-1 rounded-full">
                        {eq.type}
                      </span>

                      {user && isEligible !== undefined && (
                        <span
                          className={`text-xs px-2.5 py-1 rounded-full font-semibold flex items-center gap-1 ${
                            isEligible
                              ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                              : "bg-gray-100 text-gray-500"
                          }`}
                        >
                          {isEligible ? (
                            <>
                              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                              Eligible
                            </>
                          ) : (
                            "Check requirements"
                          )}
                        </span>
                      )}
                    </div>

                    {/* Equipment Name & Lab */}
                    <Link to={`/equipment/${eq.id}`}>
                      <h3 className="font-bold text-lg text-gray-900 group-hover:text-brand-600 transition line-clamp-1">
                        {eq.name}
                      </h3>
                    </Link>
                    <p className="text-xs text-gray-500 flex items-center gap-1 mt-1 font-medium">
                      <MapPin className="w-3.5 h-3.5 text-gray-400 shrink-0" />
                      {eq.institution || eq.lab_name}
                      {eq.city && ` · ${eq.city}`}
                    </p>

                    {/* Description */}
                    <p className="text-sm text-gray-600 mt-3 line-clamp-2 leading-relaxed">
                      {eq.description || "No description provided."}
                    </p>

                    {/* Badges/Credentials */}
                    {eq.required_credentials && eq.required_credentials.length > 0 && (
                      <div className="mt-3 flex flex-wrap gap-1">
                        {eq.required_credentials.map((c, i) => (
                          <span
                            key={i}
                            className="text-[10px] bg-amber-50 text-amber-800 border border-amber-200/80 px-2 py-0.5 rounded font-mono"
                          >
                            Requires: {c}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Card Footer */}
                  <div className="px-6 py-4 bg-gray-50/70 border-t border-gray-100 flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-1">
                        <Coins className="w-4 h-4 text-brand-600" />
                        <span className="font-extrabold text-base text-gray-900">
                          {eq.credit_per_hour}
                        </span>
                        <span className="text-xs text-gray-500">cr / hr</span>
                      </div>
                      {eq.deposit_credits > 0 && (
                        <p className="text-[10px] text-gray-400">
                          +{eq.deposit_credits} cr deposit
                        </p>
                      )}
                    </div>

                    <Link
                      to={`/equipment/${eq.id}`}
                      className="inline-flex items-center gap-1 text-xs font-bold text-brand-600 hover:text-brand-700 bg-white hover:bg-brand-50 border border-gray-200 hover:border-brand-200 px-3.5 py-2 rounded-xl transition shadow-2xs"
                    >
                      View Details <ArrowRight className="w-3.5 h-3.5" />
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

