import { NextRequest, NextResponse } from "next/server";

import { forwardGetRequest } from "@/lib/backend-proxy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 60;

type RouteContext = {
  params: {
    matterId: string;
  };
};

export async function GET(
  request: NextRequest,
  context: RouteContext
): Promise<NextResponse> {
  const matterId = encodeURIComponent(context.params.matterId);
  return forwardGetRequest(
    request,
    `/api/documents/matters/${matterId}/package/download`
  );
}
