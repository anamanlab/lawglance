import { NextRequest, NextResponse } from "next/server";

import { forwardPostRequest } from "@/lib/backend-proxy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 60;

export async function POST(request: NextRequest): Promise<NextResponse> {
  return forwardPostRequest(request, "/api/export/cases/approval");
}
