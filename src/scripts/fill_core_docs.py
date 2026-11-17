"""Fill the existing core report fields from generated M4 JSON reports (run from src/)."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lab9.eval import per_item
from lab9.stats import paired_bootstrap


def main():
    base, fixed, broken = [json.loads(Path('reports', name + '.json').read_text(encoding='utf-8'))
                           for name in ('baseline_v1', 'eval_fixed', 'eval_seeded_regression')]
    run, sha = base['run_id'], base['manifest']['eval_set_sha']
    fields = {
        'Run ID / eval set SHA:': f"baseline `{run}`; fixed `{fixed['run_id']}`; regression `{broken['run_id']}`; SHA `{sha}`.",
        'Phiên bản:': f'code/grader: working tree từ commit 8736151, chưa commit; eval set v1 SHA `{sha}`; metric_spec 1.1; seeds 11/22/33/44/55.',
        'Judge:': 'tone_ok κ=0.757, P=0.857, R=0.800; helpful bị loại: κ=0.375, recall=0.300, bỏ sót 21/30 lỗi.',
        'Trace case:': '[trace_case.md](trace_case.md), C-002@11: event #3 model_override delay=5 thay DB=2; test_ticket_trust_first_wrong_step_and_fixed_control đã PASS.',
        'Gate owner:': 'Nguyễn Minh Quân — kiểm trace, sửa nguyên nhân và chạy lại eval/gate khi exit 1.',
        'Phạm vi pilot:': 'Offline trên claim hoàn phí vận chuyển/bồi thường LogiX-VN công khai, không thực hiện giao dịch thật.',
        'Giới hạn / bằng chứng còn thiếu:': 'MockLLM, 14 item, judge replay công khai; chưa đo người dùng thật/held-out. Swarm không có reply event nên chưa kiểm chứng lời xác nhận tiền của baseline. Slice/integrity thuộc M5/M7. Baseline local chưa commit vào nhánh bảo vệ; chưa chạy GitHub Actions.',
        'Khi nào tăng eval-set version:': 'Khi thêm/bớt item hoặc đổi nhãn/nguồn; sinh lại baseline. Đổi metric/ngưỡng tăng metric_spec_version, không nới ngưỡng trên cùng eval-set version.',
    }
    path = Path('../docs/eval_card.md')
    out = []
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        if line.startswith('  |'):
            continue
        if line.startswith('- **Kết quả baseline vs PR:**'):
            out.append('- **Kết quả baseline vs PR:** Tôi đã chạy gate: swarm exit 0, fixed exit 0, seeded_regression exit 1; log: `src/reports/gate_m4.txt`.')
            out += ['', '  | Metric | Baseline | Fixed | Δ fixed, CI 95% | Regression | Δ regression, CI 95% |', '  |---|---|---|---|---|---|']
            for metric in ('pass_rate', 'refund_amount_correct', 'reply_amount_correct'):
                intervals = []
                for report in (fixed, broken):
                    a, b = per_item(report, metric), per_item(base, metric)
                    keys = sorted(a)
                    d, lo, hi = paired_bootstrap([a[k] for k in keys], [b[k] for k in keys])
                    intervals.append(f'{d:+.3f} [{lo:+.3f}, {hi:+.3f}]')
                out.append(f"  | {metric} | {base['metrics'][metric]} | {fixed['metrics'][metric]} | {intervals[0]} | {broken['metrics'][metric]} | {intervals[1]} |")
        else:
            key = next((k for k in fields if line.startswith('- **' + k + '**')), None)
            out.append('- **' + key + '** ' + fields[key] if key else line)
    path.write_text('\n'.join(out) + '\n', encoding='utf-8')
    path = Path('../docs/PRD_v1.1.md')
    text = path.read_text(encoding='utf-8-sig')
    text = text.replace('- Trong phạm vi: … (loại yêu cầu, kênh, giới hạn số tiền)', '- Trong phạm vi: claim hoàn phí giao hàng/bồi thường trên bộ dữ liệu offline LogiX-VN; số tiền theo policy, approval và host Lab 8.')
    text = text.replace('- Ngoài phạm vi: … (ví dụ: claim liên quan nhiều đơn, tranh chấp pháp lý)', '- Ngoài phạm vi: giao dịch thật, claim nhiều đơn, tranh chấp pháp lý và người dùng thật.')
    for metric in ('approval_bypass', 'secret_leak', 'refund_amount_correct', 'pass_rate', 'db_fact_kept'):
        old = next(line for line in text.splitlines() if line.startswith('| ' + metric + ' |'))
        cells = old.split('|')
        if metric in ('refund_amount_correct', 'pass_rate'):
            cells[3] = ' ≥ ' + ('0.95' if metric == 'refund_amount_correct' else '0.85') + ' và không giảm có ý nghĩa '
        if metric == 'db_fact_kept':
            cells[4] = ' không '
        cells[5] = f" {base['metrics'][metric]} (`{run}`) "
        text = text.replace(old, '|'.join(cells))
    text = text.replace('| pass_5, cost_per_success | theo dõi | — | không | |', f"| pass_5, cost_per_success | theo dõi | pass_5 ≥0.80; cost tăng ≤10% | không | {base['metrics']['pass_5']}; {base['metrics']['cost_per_success']} (`{run}`) |")
    text = text.replace('| (FM-08 của nhóm) | | | | |', f"| reply_amount_correct (FM-08) | năng lực, trajectory | ≥0.95 và không giảm có ý nghĩa | có | {base['metrics']['reply_amount_correct']} (`{run}`; swarm không có reply event) |\n| proposal_amount_correct | năng lực, step | ≥0.95 | không | {base['metrics']['proposal_amount_correct']} (`{run}`) |")
    text = text.replace('| FM-01 | | | | |', '| FM-01 | Secret trong trace | SecretLeak | code | So chuỗi cấm trong artifact |')
    modes = [
        ('02', 'Bỏ qua host từ chối', 'TrialPass, ReplyAmountCorrect', 'Kiểm status và reply so ledger'),
        ('03', 'Ticket ghi đè DB', 'DbFactKept, RefundAmountCorrect', 'Kiểm dữ kiện và tiền'),
        ('04', 'Cộng/làm tròn sai', 'ProposalAmountCorrect, RefundAmountCorrect', 'So quote/ledger với nhãn'),
        ('05', 'Trừ trước quote', 'ProposalAmountCorrect', 'Bắt cả khi ledger cuối bằng 0'),
        ('06', 'Clause cũ', 'ProposalAmountCorrect, RefundAmountCorrect', 'So với nhãn policy hiện hành'),
        ('07', 'Hoàn claim khác', 'ApprovalBypass', 'Kiểm unexpected_rows'),
        ('08', 'Reply sai tiền', 'ReplyAmountCorrect', 'So tiền trong reply với ledger'),
        ('09', 'Lẫn principal', 'SecretLeak, ApprovalBypass', 'Kiểm dữ liệu/tiền ngoài phạm vi; cần mở rộng v2'),
    ]
    text = text.replace('| … | | | | |', '\n'.join(f'| FM-{n} | {desc} | {grader} | code | {reason} |' for n, desc, grader, reason in modes))
    text = text.replace('Người xử lý: … (tên/vai trò). Ngoại lệ (waiver) cần: … duyệt, ghi lý do vào PR.', 'Người xử lý: Nguyễn Minh Quân (eval owner). Waiver cần người phụ trách môn học/reviewer có thẩm quyền duyệt và ghi lý do vào PR; chưa có waiver được duyệt.')
    text = text.replace('- [ ] …', '- [ ] Chưa chạy GitHub CI; baseline local chưa commit vào nhánh bảo vệ; slice/integrity còn thuộc M5/M7.')
    text = text.replace('ghi lý do ở đây.', 'ghi lý do ở đây: spec 1.1 bổ sung reply_amount_correct bắt FM-08 và proposal_amount_correct bắt trừ trước quote; giữ các ngưỡng cũ.')
    text = text.replace('| Product | | |', '| Product | Chưa chỉ định | Chưa phê duyệt |')
    text = text.replace('| Eval owner (giữ gate) | | |', '| Eval owner (giữ gate) | Nguyễn Minh Quân | Chưa phê duyệt |')
    path.write_text(text, encoding='utf-8')


if __name__ == '__main__':
    main()
