import { NextRequest, NextResponse } from "next/server";

import { forwardPostRequest } from "@/lib/backend-proxy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 60;

type RouteContext = {
  params: {
    matterId: string;
  };
};

export async function POST(
  request: NextRequest,
  context: RouteContext
): Promise<NextResponse> {
  const matterId = encodeURIComponent(context.params.matterId);
  return forwardPostRequest(request, `/api/documents/matters/${matterId}/package`);
}
