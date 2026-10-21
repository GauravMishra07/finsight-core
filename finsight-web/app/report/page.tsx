import { Suspense } from "react";
import ReportView from "@/components/ReportView";

// useSearchParams needs a Suspense boundary under static export.
export default function ReportPage() {
  return (
    <Suspense>
      <ReportView />
    </Suspense>
  );
}
