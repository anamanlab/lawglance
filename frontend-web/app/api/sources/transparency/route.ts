import { NextRequest, NextResponse } from "next/server";

import { forwardGetRequest } from "@/lib/backend-proxy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 60;

export async function GET(request: NextRequest): Promise<NextResponse> {
  return forwardGetRequest(request, "/api/sources/transparency");
}
