/** Required wherever member purchase data appears: it is generated, never real. */
export function SyntheticBanner() {
  return (
    <div className="banner" role="note">
      <p>
        <strong>Synthetic demo data.</strong> The facilities and purchase lines on this page are
        generated with a fixed random seed from public price distributions. They do not describe
        any real hospital or purchase.
      </p>
    </div>
  );
}
