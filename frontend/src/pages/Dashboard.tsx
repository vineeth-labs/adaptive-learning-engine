import { Target } from "lucide-react";

import { useCompetencyMap, useNextRecommendation } from "../api/hooks";
import { USER_ID } from "../api/config";
import { ConceptDeepDive } from "../components/dashboard/ConceptDeepDive";
import { MasteryRadar } from "../components/dashboard/MasteryRadar";
import { RecommendationHero } from "../components/dashboard/RecommendationHero";
import { TopBadges } from "../components/layout/TopBadges";

// TODO: target role / display name have no backend source yet — placeholders.
const USER_NAME = "Alex";
const TARGET_ROLE = "Java Backend Engineer";

export function Dashboard() {
  const map = useCompetencyMap(USER_ID);
  const rec = useNextRecommendation(USER_ID);

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      {/* HEADER */}
      <div className="flex flex-col md:flex-row md:items-end justify-between mb-8 gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 mb-1">
            Welcome back, {USER_NAME}
          </h1>
          <div className="flex items-center text-slate-600">
            <Target size={16} className="mr-2 text-indigo-500" />
            <span>
              Target Role:{" "}
              <strong className="text-slate-800">{TARGET_ROLE}</strong>
            </span>
          </div>
        </div>
        <TopBadges />
      </div>

      {/* HERO: next recommendation */}
      {rec.isLoading ? (
        <HeroSkeleton />
      ) : rec.isError ? (
        <ErrorCard
          title="Couldn't load your recommendation"
          message={(rec.error as Error).message}
        />
      ) : (
        rec.data && <RecommendationHero rec={rec.data} />
      )}

      {/* METRICS GRID */}
      {map.isLoading ? (
        <CardSkeleton />
      ) : map.isError ? (
        <ErrorCard
          title="Couldn't load your competency map"
          message={(map.error as Error).message}
        />
      ) : (
        map.data && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <MasteryRadar nodes={map.data.nodes} targetRole={TARGET_ROLE} />
            <ConceptDeepDive nodes={map.data.nodes} />
          </div>
        )
      )}
    </div>
  );
}

function HeroSkeleton() {
  return (
    <div className="mb-8 h-48 rounded-3xl bg-slate-200 animate-pulse" />
  );
}

function CardSkeleton() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
      <div className="h-96 rounded-3xl bg-slate-200 animate-pulse lg:col-span-1" />
      <div className="h-96 rounded-3xl bg-slate-200 animate-pulse lg:col-span-2" />
    </div>
  );
}

function ErrorCard({ title, message }: { title: string; message: string }) {
  return (
    <div className="mb-8 rounded-3xl border border-red-200 bg-red-50 p-6">
      <h3 className="font-bold text-red-800">{title}</h3>
      <p className="text-sm text-red-600 mt-1 break-words">{message}</p>
      <p className="text-xs text-red-500 mt-3">
        Tip: set <code>VITE_USE_MOCKS=true</code> to render with mock data, or
        ensure the backend is running and CORS allows this origin.
      </p>
    </div>
  );
}
