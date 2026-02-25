import { NextRequest, NextResponse } from "next/server";

import { forwardPostRequest } from "@/lib/backend-proxy";

export const runtime = "nodejs";

export async function POST(request: NextRequest): Promise<NextResponse> {
  return forwardPostRequest(request, "/api/research/lawyer-cases");
}
