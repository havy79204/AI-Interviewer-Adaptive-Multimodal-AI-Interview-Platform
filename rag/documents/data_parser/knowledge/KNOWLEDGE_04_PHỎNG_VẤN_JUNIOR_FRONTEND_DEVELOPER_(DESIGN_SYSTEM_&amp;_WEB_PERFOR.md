## [TÀI LIỆU 04] PHỎNG VẤN JUNIOR FRONTEND DEVELOPER (DESIGN SYSTEM &amp; WEB PERFORMANCE)

1. Định vị chức danh &amp; Ngành nghề cốt lõi
- Vị trí: Junior Frontend Developer (React / Next.js hoặc Vue.js / Nuxt).
- Cấp bậc: Junior (1 - 2.5 năm kinh nghiệm).
- Domain tiêu biểu: Digital Agency, Sản phẩm truyền thông / Báo chí điện tử, E-commerce storefront, FinTech Mobile Web.
- Mục tiêu then chốt trong buổi phỏng vấn: Đánh giá mức độ thấu hiểu sâu sắc về nền tảng Web (HTML/CSS/JS thuần), khả năng hiện thực hóa bản thiết kế Figma chuẩn xác (Pixel-perfect), tư duy Component tái sử dụng và nhận thức về tối ưu hiệu năng trang (Web Vitals).
2. Hệ sinh thái vai trò &amp; Hội đồng phỏng vấn
- Người phỏng vấn chính: Senior Frontend Engineer, UI/UX Lead.
- Giao diện làm việc thực tế: Nhận file thiết kế từ UI/UX Designer, tích hợp API từ Backend Dev, tiếp nhận bug hiển thị từ QA Tester trên các thiết bị di động thực tế.
3. Công nghệ xu hướng &amp; Khái niệm bắt buộc
- Core Web &amp; Styling: CSS Grid/Flexbox nâng cao, Tailwind CSS, CSS Variables, Container Queries, Responsive Design strategy (Mobile-first).
- JavaScript / TypeScript: Event Loop, Closures, DOM manipulation bản chất, TypeScript interfaces/types, Async handling.
- Framework internals: React Hooks (useCallback, useMemo, useRef), Virtual DOM reconciliation vs Fine-grained reactivity, Vue 3 Composition API.
- Web Vitals &amp; Performance: LCP (Largest Contentful Paint), CLS (Cumulative Layout Shift), INP (Interaction to Next Paint), Image lazy loading, Code-splitting.
4. Kịch bản phỏng vấn kỹ thuật &amp; Tình huống "bắt bài"
- Câu hỏi bản chất JavaScript (Bắt bài học vẹt framework): "Event Loop trong trình duyệt hoạt động như thế nào? Sự khác biệt giữa Microtask Queue (Promises) và Macrotask Queue (setTimeout) là gì? Đoạn mã sau sẽ in ra thứ tự nào?"
- JavaScript

console.log('1'); setTimeout(() =&gt; console.log('2'), 0); Promise.resolve().then(() =&gt; console.log('3')); console.log('4');

- ●
- Kỳ vọng: Trả lời đúng thứ tự: 1 -&gt; 4 -&gt; 3 -&gt; 2 và giải thích cặn kẽ: Call Stack thực thi code đồng bộ trước (1, 4), sau đó ưu tiên dọn sạch Microtask Queue (3), rồi mới chuyển sang lấy tác vụ từ Macrotask Queue (2).
- Thử thách CSS &amp; Layout (Live Test): Cho một bản thiết kế thẻ Card phức tạp với chữ tiêu đề dài ngắn bất định và yêu cầu nút bấm luôn phải bám sát đáy thẻ (sticky bottom), đồng thời không được để vỡ giao diện khi người dùng zoom chữ lên 200%.
- Kỳ vọng: Dùng Flexbox với flex-direction: column và gán margin-top: auto cho nút bấm; sử dụng đơn vị tương đối rem/em thay vì cố định px.
- Tình huống tối ưu trải nghiệm (Performance &amp; UX): "Làm thế nào để xây dựng một ô tìm kiếm (Search Box) tự động gợi ý kết quả khi người dùng gõ phím mà không gửi hàng chục request làm nghẽn server và không làm đơ giao diện gõ chữ?"
- Kỳ vọng: Áp dụng kỹ thuật Debounce (trì hoãn gửi request khoảng 300ms sau lần gõ cuối); hủy bỏ request cũ nếu request mới đã được phát đi (dùng AbortController); xử lý trạng thái hiển thị loading mượt mà.
5. Sự cố phòng phỏng vấn &amp; Cách làm chủ không gian
- Môi trường Online:
- Sự cố: Trình duyệt hiển thị sai hoặc CSS bị vỡ khi đang live code trước mặt người phỏng vấn.
- Xử lý: Đừng cuống cuồng bấm Ctrl + Z. Hãy bình tĩnh mở ngay Chrome DevTools (F12), dùng tính năng Inspect Element để chỉ cho người phỏng vấn thấy bạn đang phân tích thuộc tính CSS nào đang gây lỗi (overflow, z-index, hoặc display). Người phỏng vấn đánh giá cao kỹ năng debug thực tế hơn là việc không bao giờ mắc lỗi.
- Môi trường Onsite:
- Điện thoại cá nhân: Tuyệt đối tắt chuông hoặc chuyển sang chế độ im lặng hoàn toàn (không để rung trên mặt bàn vì tiếng rung cộng hưởng với mặt bàn gỗ gây mất tập trung cực lớn). Nếu dùng điện thoại để xem bản demo sản phẩm đã làm, hãy chuẩn bị sẵn app ở trạng thái mở.