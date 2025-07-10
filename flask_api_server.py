from flask import Flask, request, jsonify
from flask import render_template
from flask_cors import CORS
import json
import base64
import os
from datetime import datetime

# استيراد كلاس قاعدة البيانات (يجب أن يكون في نفس المجلد)
from handjet_db import HandJetProblemDB

# تحديد مسار templates بشكل صحيح
current_dir = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=current_dir)
CORS(app)  # للسماح بطلبات من المتصفح

# إنشاء مثيل من قاعدة البيانات
db = HandJetProblemDB("./data/handjet_problems.db")


# المسار الرئيسي لعرض الواجهة
@app.route('/')
def index():
    # التحقق من وجود الملف أولاً
    template_path = os.path.join(current_dir, 'hi-tech-final.html')
    if not os.path.exists(template_path):
        return f"""
        <html dir="rtl">
        <body>
        <h1>خطأ: ملف hi-tech-final.html غير موجود</h1>
        <p>المسار المطلوب: {template_path}</p>
        <p>الملفات الموجودة في المجلد:</p>
        <ul>
        {''.join([f'<li>{f}</li>' for f in os.listdir(current_dir) if f.endswith('.html')])}
        </ul>
        </body>
        </html>
        """

    return render_template('hi-tech-final.html')


# API للحصول على جميع المشاكل
@app.route('/api/problems', methods=['GET'])
def get_problems():
    try:
        # جلب جميع المشاكل أولاً
        problems_data = db.get_problems()

        # جلب معلومات العملاء والفنيين للربط
        clients = db.get_clients()
        technicians = db.get_technicians()

        # إنشاء قواميس للمعرفات لسهولة البحث
        clients_map = {client['id']: client for client in clients}
        technicians_map = {tech['id']: tech for tech in technicians}

        # دمج بيانات العميل والفني مع بيانات المشكلة
        problems_with_details = []
        for problem in problems_data:
            problem_dict = dict(problem)  # تحويل صفوف SQLite إلى قاموس

            # إضافة بيانات العميل
            client_id = problem_dict.get('client_id')
            if client_id and client_id in clients_map:
                problem_dict['client_name'] = clients_map[client_id]['name']
                problem_dict['client_phone_number'] = clients_map[client_id]['contact_phone']
            else:
                problem_dict['client_name'] = 'غير معروف'
                problem_dict['client_phone_number'] = 'غير معروف'

            # إضافة بيانات الفني
            technician_id = problem_dict.get('technician_id')
            if technician_id and technician_id in technicians_map:
                problem_dict['technician_name'] = technicians_map[technician_id]['name']
            else:
                problem_dict['technician_name'] = 'لم يتم التعيين'

            problems_with_details.append(problem_dict)

        return jsonify(problems_with_details)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# API لإضافة مشكلة جديدة
@app.route('/api/problems', methods=['POST'])
def add_problem():
    data = request.get_json()
    try:
        problem_id = db.add_problem(
            title=data['title'],
            description=data.get('description'),
            model=data['model'],
            serial_number=data['serial_number'],
            client_id=data['client_id'],  # يجب أن يكون معرف العميل موجوداً
            error_code=data.get('error_code'),
            component=data.get('component'),
            ink_type=data.get('ink_type'),
            surface_type=data.get('surface_type'),
            priority=data.get('priority', 2),
            image_path=data.get('image_path'),
            reported_by=data.get('reported_by')
        )
        return jsonify({"message": "تمت إضافة المشكلة بنجاح", "id": problem_id}), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"خطأ في إضافة المشكلة: {str(e)}"}), 500


# API لتحديث حالة المشكلة
@app.route('/api/problems/<int:problem_id>/status', methods=['PUT'])
def update_problem_status_api(problem_id):
    data = request.get_json()
    status = data.get('status')
    if not status:
        return jsonify({"error": "الحالة مطلوبة"}), 400
    try:
        db.update_problem_status(problem_id, status)
        return jsonify({"message": f"تم تحديث حالة المشكلة {problem_id} إلى {status}"})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"خطأ في تحديث الحالة: {str(e)}"}), 500


# API لتعديل تفاصيل المشكلة
@app.route('/api/problems/<int:problem_id>', methods=['PUT'])
def update_problem_api(problem_id):
    data = request.get_json()
    try:
        # استخدام دالة تحديث المشكلة (لم يتم توفيرها، لكن يمكن إنشاؤها في HandJetProblemDB)
        # مؤقتاً، سنقوم بتحديث الحالة والفني المعين فقط
        # في تطبيق متكامل، يجب أن تكون هناك دالة update_problem_details في handjet_db.py
        # تقوم بتحديث كافة الحقول الممكنة.

        # لتحديث الحقول الممكنة حاليًا
        update_fields = {}
        if 'status' in data:
            update_fields['status'] = data['status']
        if 'technician_id' in data:  # هذا يفترض أن الفني يتم تعيينه عبر ID
            update_fields['technician_id'] = data['technician_id']

        # يمكن إضافة المزيد من الحقول هنا لتحديثها (مثال: priority, description, etc.)
        # بما أن دالة `update_problem_status` فقط هي الموجودة، سنستخدمها
        if 'status' in update_fields:
            db.update_problem_status(problem_id, update_fields['status'])
            # إذا كان هناك حقل technician_id أيضاً، يجب استدعاء دالة تحديث أخرى
            # أو دالة عامة لتحديث المشكلة في HandJetProblemDB
            # في الوقت الحالي، لا توجد دالة عامة لتحديث جميع حقول المشكلة دفعة واحدة.
            # سنقوم فقط بإرجاع رسالة نجاح إذا تم تمرير الحالة.
            return jsonify({"message": f"تم تحديث المشكلة {problem_id} بنجاح. تم تحديث الحالة."})

        # إذا لم يتم تمرير حقل الحالة، ولكن تم تمرير حقول أخرى مثل technician_id
        # سيتطلب هذا وجود دالة update_problem في handjet_db.py
        # نظراً لعدم وجودها حالياً، سنفترض تحديث الحالة فقط.
        return jsonify({"error": "لا توجد حقول صالحة للتحديث أو دالة تحديث المشكلة غير موجودة"}), 400

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"خطأ في تحديث المشكلة: {str(e)}"}), 500


# API للحصول على حلول مشكلة معينة
@app.route('/api/problems/<int:problem_id>/solutions', methods=['GET'])
def get_solutions(problem_id):
    try:
        solutions = db.get_solutions_for_problem(problem_id)
        return jsonify(solutions)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# API لإضافة حل جديد لمشكلة
@app.route('/api/problems/<int:problem_id>/solutions', methods=['POST'])
def add_solution(problem_id):
    data = request.get_json()
    try:
        solution_id = db.add_solution(
            problem_id=problem_id,
            title=data['title'],
            steps=data['steps'],
            tools_needed=data.get('tools_needed'),
            time_required=data.get('time_required'),
            solution_type=data.get('solution_type'),
            difficulty_level=data.get('difficulty_level', 2),
            notes=data.get('notes'),
            created_by=data.get('created_by')
        )
        return jsonify({"message": "تمت إضافة الحل بنجاح", "id": solution_id}), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"خطأ في إضافة الحل: {str(e)}"}), 500


# API لتقييم حل
@app.route('/api/solutions/<int:solution_id>/rate', methods=['POST'])
def rate_solution_api(solution_id):
    data = request.get_json()
    rating = data.get('rating')
    feedback = data.get('feedback')
    rated_by = data.get('rated_by')
    if rating is None or not (1 <= rating <= 5):
        return jsonify({"error": "التقييم يجب أن يكون رقماً بين 1 و 5"}), 400
    try:
        db.rate_solution(solution_id, rating, feedback, rated_by)
        return jsonify({"message": "تم تقييم الحل بنجاح"})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"خطأ في تقييم الحل: {str(e)}"}), 500


# API للحصول على إحصائيات النظام
@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    try:
        stats = db.get_system_statistics()
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# API للحصول على معلومات قاعدة البيانات
@app.route('/api/db_info', methods=['GET'])
def get_db_info():
    try:
        info = db.get_database_info()
        return jsonify(info)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# API لإنشاء بيانات تجريبية (للتجربة والتطوير)
@app.route('/api/create_dummy_data', methods=['POST'])
def create_dummy_data():
    try:
        # حذف قاعدة البيانات القديمة إذا وجدت
        if os.path.exists("./data/handjet_problems.db"):
            os.remove("./data/handjet_problems.db")
            print("Old database removed.")

        # إعادة تهيئة قاعدة البيانات (لإنشاء الجداول من جديد)
        global db
        db = HandJetProblemDB("./data/handjet_problems.db")
        print("Database re-initialized and tables created.")

        # إضافة عميل تجريبي
        client_id = db.add_client(
            name="شركة الطباعة السريعة",
            contact_phone="0501234567",
            email="contact@fastprint.com",
            company="Fast Print Co.",
            service_contract=True,
            location="الرياض"
        )
        print(f"Added client with ID: {client_id}")

        client_id_2 = db.add_client(
            name="مؤسسة النور للطباعة",
            contact_phone="0559876543",
            email="alnoor@example.com",
            company="Al-Noor Printing",
            service_contract=False,
            location="جدة"
        )
        print(f"Added client with ID: {client_id_2}")

        # إضافة فنيين تجريبيين
        technician_id_1 = db.add_technician(name="أحمد فني", specialty="كهرباء", contact="0501112222",
                                            certification_level=3)
        technician_id_2 = db.add_technician(name="محمد فني", specialty="برمجيات", contact="0503334444",
                                            certification_level=4)
        print(f"Added technician Ahmed with ID: {technician_id_1}")
        print(f"Added technician Mohamed with ID: {technician_id_2}")

        # إضافة مشاكل تجريبية
        problems_data = [
            {
                'title': 'مشكلة في رأس الطباعة',
                'description': 'الخطوط الأفقية غير واضحة.',
                'model': 'HandJet EBS-250',
                'serial_number': 'SN-HJ250-001',
                'client_id': client_id,
                'error_code': 'E101',
                'component': 'Print Head',
                'ink_type': 'Quick Dry',
                'surface_type': 'Plastic',
                'priority': 1,
                'reported_by': 'المستخدم',
                'failure_cause': 'hardware',
                'technician_id': technician_id_1  # تعيين فني
            },
            {
                'title': 'خطأ في الاتصال بالشبكة',
                'description': 'الطابعة لا تتصل بشبكة Wi-Fi.',
                'model': 'HandJet EBS-260',
                'serial_number': 'SN-HJ260-002',
                'client_id': client_id_2,
                'error_code': 'N202',
                'component': 'Network Module',
                'ink_type': 'Standard',
                'surface_type': 'Paper',
                'priority': 2,
                'reported_by': 'المدير',
                'failure_cause': 'software',
                'technician_id': technician_id_2  # تعيين فني
            },
            {
                'title': 'توقف مفاجئ عن الطباعة',
                'description': 'تتوقف الطابعة عن العمل بعد بضع دقائق.',
                'model': 'HandJet EBS-250',
                'serial_number': 'SN-HJ250-003',
                'client_id': client_id,
                'error_code': 'P303',
                'component': 'Power Supply',
                'ink_type': 'UV',
                'surface_type': 'Glass',
                'priority': 3,
                'reported_by': 'المشغل',
                'failure_cause': 'hardware',
                'technician_id': None  # لم يتم تعيين فني
            }
        ]

        problem_ids = []
        for p_data in problems_data:
            p_id = db.add_problem(**p_data)
            problem_ids.append(p_id)
            print(f"Added problem with ID: {p_id}")

        # إضافة حلول تجريبية لمشاكل موجودة
        solutions = [
            {
                'problem_id': problem_ids[0],
                'title': 'استبدال رأس الطباعة',
                'steps': '1. قم بإيقاف تشغيل الجهاز. 2. أزل رأس الطباعة القديم. 3. ركب رأس الطباعة الجديد. 4. قم بإجراء معايرة.',
                'difficulty_level': 4
            },
            {
                'problem_id': problem_ids[1],
                'title': 'إعادة ضبط إعدادات الشبكة',
                'steps': '1. انتقل إلى قائمة الإعدادات. 2. اختر الشبكة. 3. قم بإعادة ضبط المصنع لإعدادات Wi-Fi.',
                'difficulty_level': 2
            },
            {
                'problem_id': problem_ids[0],  # حل آخر لنفس المشكلة
                'title': 'تنظيف رأس الطباعة يدوياً',
                'steps': '1. افصل الطاقة. 2. استخدم قطعة قماش خالية من الوبر ومحلول تنظيف خاص لرأس الطباعة. 3. اتركها لتجف قبل إعادة التشغيل.',
                'difficulty_level': 2
            }
        ]

        for solution_data in solutions:
            db.add_solution(
                problem_id=solution_data['problem_id'],
                title=solution_data['title'],
                steps=solution_data['steps'],
                difficulty_level=solution_data['difficulty_level'],
                created_by="النظام التجريبي"
            )

        return jsonify({
            'success': True,
            'message': 'تم إنشاء البيانات التجريبية بنجاح',
            'client_ids': [client_id, client_id_2],
            'technician_ids': [technician_id_1, technician_id_2],
            'problem_ids': problem_ids
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# --- API جديدة لإدارة العملاء ---
@app.route('/api/clients', methods=['POST'])
def add_client_api():
    data = request.get_json()
    try:
        client_id = db.add_client(
            name=data['name'],
            contact_phone=data['contact_phone'],
            email=data.get('email'),
            company=data.get('company'),
            service_contract=data.get('service_contract', False),
            location=data.get('location')
        )
        return jsonify({"message": "تمت إضافة العميل بنجاح", "id": client_id}), 201
    except Exception as e:
        return jsonify({"error": f"خطأ في إضافة العميل: {str(e)}"}), 500


@app.route('/api/clients', methods=['GET'])
def get_clients_api():
    try:
        clients = db.get_clients()
        return jsonify(clients)
    except Exception as e:
        return jsonify({"error": f"خطأ في جلب العملاء: {str(e)}"}), 500


# --- API جديدة لإدارة الفنيين ---
@app.route('/api/technicians', methods=['POST'])
def add_technician_api():
    data = request.get_json()
    try:
        technician_id = db.add_technician(
            name=data['name'],
            specialty=data.get('specialty'),
            contact=data.get('contact'),
            certification_level=data.get('certification_level')
        )
        return jsonify({"message": "تمت إضافة الفني بنجاح", "id": technician_id}), 201
    except Exception as e:
        return jsonify({"error": f"خطأ في إضافة الفني: {str(e)}"}), 500


@app.route('/api/technicians', methods=['GET'])
def get_technicians_api():
    try:
        technicians = db.get_technicians()
        return jsonify(technicians)
    except Exception as e:
        return jsonify({"error": f"خطأ في جلب الفنيين: {str(e)}"}), 500


if __name__ == '__main__':
    # إنشاء مجلد البيانات إذا لم يكن موجوداً
    os.makedirs('./data', exist_ok=True)

    # طباعة معلومات التشخيص
    print(" System Diagnosis🔍:")
    print(f"Current working folder 📁: {current_dir}")
    print(f"HTML file exists 📄: {os.path.exists(os.path.join(current_dir, 'hi-tech-final.html'))}")
    print(f"Files in the folder 📋 : {[f for f in os.listdir(current_dir) if f.endswith('.html')]}")

    print("\n Hi-Tech's technical support system has been launched🚀...")
    print("The interface is available on 📊: http://localhost:1406")



    # تشغيل الخادم
    app.run(debug=True, host='0.0.0.0', port=1406)