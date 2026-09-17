"use client";

/** The model's top greenfield targets, with navigable coordinates.
 *
 * Typography and controls are the existing workspace scale only: `section-label`
 * from the survey panels, Badge for the rank, Button `link` for the disclosure
 * (as components/mines/mine-roster.tsx uses), mono `tabular-nums` for
 * coordinates. No new tokens.
 *
 * Every row states what it is: a cell centre from the served heatmap, refined
 * once, on ground outside the 5 km occurrence buffer. The coordinate is good to
 * the stated precision and no better.
 */

import { useState } from "react";
import { Check, Copy, Crosshair, ExternalLink } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { Target } from "@/lib/contracts";
import { useTopTargets } from "@/hooks/use-top-targets";

function coordinates(target: Target): string {
  return `${target.location.latitude.toFixed(4)}, ${target.location.longitude.toFixed(4)}`;
}

function TargetRow({
  target,
  selected,
  onSelect,
}: {
  target: Target;
  selected: boolean;
  onSelect: (target: Target) => void;
}) {
  const [copied, setCopied] = useState(false);
  const text = coordinates(target);

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard can be blocked; the coordinate is on screen to read off.
    }
  }

  return (
    <li className="target-row">
      <button
        type="button"
        className="target-row-head"
        aria-expanded={selected}
        onClick={() => onSelect(target)}
      >
        <Badge variant={target.rank <= 3 ? "default" : "secondary"}>{target.id}</Badge>
        <span className="target-row-label">{target.label}</span>
        <span className="font-mono text-xs tabular-nums">{target.score.toFixed(2)}</span>
      </button>
      {selected && (
        <div className="target-row-detail">
          <p className="font-mono text-xs tabular-nums">{text}</p>
          <div className="target-row-actions">
            <Button variant="outline" size="sm" onClick={copy}>
              {copied ? <Check size={13} aria-hidden="true" /> : <Copy size={13} aria-hidden="true" />}
              {copied ? "Copied" : "Copy"}
            </Button>
            <Button variant="outline" size="sm" asChild>
              <a
                href={`https://www.google.com/maps/search/?api=1&query=${target.location.latitude},${target.location.longitude}`}
                target="_blank"
                rel="noreferrer"
              >
                <ExternalLink size={13} aria-hidden="true" />
                Open in Maps
              </a>
            </Button>
          </div>
          <dl className="target-row-facts">
            <div>
              <dt>Distance</dt>
              <dd>
                {Math.round(target.km_to_nearest_mine)} km {target.bearing_from_mine} of{" "}
                {target.nearest_mine}
              </dd>
            </div>
            <div>
              <dt>Neighbourhood</dt>
              <dd>{target.neighbourhood_score.toFixed(2)} mean of adjacent cells</dd>
            </div>
            <div>
              <dt>Coordinate precision</dt>
              <dd>± {target.precision_m} m</dd>
            </div>
            <div>
              <dt>Status</dt>
              <dd>Outside the 5 km occurrence buffer</dd>
            </div>
          </dl>
        </div>
      )}
    </li>
  );
}

export function TargetPanel({
  selectedId,
  onSelect,
}: {
  selectedId: string | null;
  onSelect: (target: Target | null) => void;
}) {
  const { targets, loading, error } = useTopTargets();

  return (
    <div className="target-panel">
      <div className="survey-intro">
        <p className="section-label">
          <Crosshair size={13} aria-hidden="true" /> Model targets
        </p>
        <p className="text-xs leading-5 text-muted-foreground">
          The ten highest-scoring places the model picks out on ground nobody is
          already mining. Ranked by score, then by how strongly the surrounding
          cells score — a lone hot cell beside cold ground is more likely noise
          than a deposit.
        </p>
      </div>

      {loading && (
        <p className="note" role="status">
          Scoring the belt and refining each target…
        </p>
      )}
      {error && (
        <p className="note" role="alert">
          Targets unavailable — {error}
        </p>
      )}

      {targets && (
        <>
          <ul className="target-list">
            {targets.targets.map((target) => (
              <TargetRow
                key={target.id}
                target={target}
                selected={selectedId === target.id}
                onSelect={(chosen) => onSelect(selectedId === chosen.id ? null : chosen)}
              />
            ))}
          </ul>
          <p className="note">
            Screening indices, not drill targets: {targets.candidates_considered} cells
            qualified and every one of these sits at the {targets.targets[0]?.score.toFixed(2)}{" "}
            cap, so the order comes from the neighbourhood measure rather than the score.
            Targets are kept at least {targets.min_separation_km} km apart so one anomaly
            cannot fill the list.
          </p>
        </>
      )}
    </div>
  );
}
