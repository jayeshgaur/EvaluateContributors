import { promises as fs } from "fs";
import path from "path";
import Dashboard from "@/app/components/Dashboard";
import { ResultsData } from "@/app/types";

export default async function Page() {
  const filePath = path.join(process.cwd(), "public", "results.json");
  const raw = await fs.readFile(filePath, "utf-8");
  const data: ResultsData = JSON.parse(raw);

  return <Dashboard data={data} />;
}
