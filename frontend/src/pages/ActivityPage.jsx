import { ActivityFeed } from "../components/ActivityFeed";
import { PageHeader } from "../components/ui";

export function ActivityPage() {
  return (
    <div>
      <PageHeader
        kicker="Activity"
        title="What students are doing"
        lede="The feed polls GET /teacher/activity every few seconds. Newest events are first."
      />
      <ActivityFeed limit={50} />
    </div>
  );
}
