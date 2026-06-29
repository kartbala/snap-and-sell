import SSIcon from "./SSIcon";
import { fmtPrice, track } from "../ssUtils";

const SMS_NUMBER = "+12026846252";

function smsHref(item) {
  const body = `Hi! Interested in "${item.title}" at ${fmtPrice(item.current_price ?? item.asking_price)}.`;
  return `sms:${SMS_NUMBER}?&body=${encodeURIComponent(body)}`;
}

export default function OfferForm({ item }) {
  return (
    <div className="ss-offer-buttons">
      <a
        href={smsHref(item)}
        className="ss-btn ss-btn-primary"
        onClick={() => track("contact_click", { listingId: item.id, target: "sms" })}
      >
        <SSIcon name="sms" size={20} stroke={2} /> Text Karthik
      </a>
    </div>
  );
}
