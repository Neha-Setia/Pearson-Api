from flask import Flask, render_template, request, jsonify, url_for, send_from_directory

import json,os,pymongo,ssl
from watson_developer_cloud import DiscoveryV1
from werkzeug.utils import secure_filename
import base64, pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from werkzeug.datastructures import FileStorage

MONGODB_URL = "mongodb://admin:DFBRISRYRDWHRYWP@bluemix-sandbox-dal-9-portal.7.dblayer.com:25934,bluemix-sandbox-dal-9-portal.6.dblayer.com:25934/admin?ssl=true"
# MONGODB_URL = os.environ.get('MONGODB_URL')

client = pymongo.MongoClient(MONGODB_URL, ssl_cert_reqs=ssl.CERT_NONE)
print(client)
db = client.discovery_db
coll = db.Pearsons_maths_dictionary

UPLOAD_FOLDER = './uploads'


app = Flask(__name__)
app._static_folder = './static'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

discovery = DiscoveryV1(
    '2016-11-07',
    username='5f10f086-cd37-4386-bffe-f4e829e589a8',
    password='crMQG1F3jQuR')

environments = discovery.get_environments()
print(environments)

my_environment = [x for x in environments['environments'] if x['name'] == 'byod']
environment_id = my_environment[0]['environment_id']
print(environment_id)


#####################  COLLECTION ID  FOR EDU DCOS ##################
collections = discovery.list_collections(environment_id)
doc_collection = [x for x in collections['collections'] if x['name'] == 'pearson-api']
doc_collection_id = doc_collection[0]['collection_id']
print(doc_collection_id)
#4ee23389-04fa-4ecf-9811-957bcecb19b4

configuration_id = discovery.get_default_configuration_id(environment_id=environment_id)
print(configuration_id)

# api_endpoint = "https://gateway.watsonplatform.net/discovery/api/v1"
username = '5f10f086-cd37-4386-bffe-f4e829e589a8'
password = 'crMQG1F3jQuR'
document_id_list =[]


def decode_base64(data):
    """Decode base64, padding being optional.

    :param data: Base64 data as an ASCII byte string
    :returns: The decoded byte string.

    """
    missing_padding = len(data) % 4
    if missing_padding != 0:
        data += b'=' * (4 - missing_padding)
    return base64.b64decode(data)

@app.route("/")
def main():
    return render_template('document-upload.html')


@app.route("/upload", methods=['POST'])
def upload_document():
    print("upload")
    print(request)
    print(request.data)
    file = request.data

    file = file.split(',')
    file = decode_base64(file[1])
    print(file)
    file1 = FileStorage(stream=file, name="division.pdf")
    print(file1.stream)
    # f = file1.filename
    # print(f)
    # # file2 = stream.read()
    # # print(file2)
    # # file_result = open('./uploads/filename1.json', 'wb')  # create a writable file and write the decoding result
    # # file_result.write(file)
    #
    # # with open(os.path.join(app.config['UPLOAD_FOLDER'], 'filename1.json')) as fileinfo:
    # #     print(fileinfo)
    # files=[]
    # files.append((f, FileStorage(stream=file, filename="division.pdf")))
    # print(files[0])

    add_doc = discovery.add_document(environment_id, doc_collection_id, file_info=file1)
    d = json.dumps(add_doc, indent=2)
    print(d)
    document_id_list.append(add_doc['document_id'][0])
    print(document_id_list[0])

    print("hi")
    qopts = {'query': ''}
    my_query = discovery.query(environment_id, doc_collection_id, qopts)
    print(my_query)

    # data = [q['enriched_text'] for q in my_query['results']]
    data = my_query['results'][0]['enriched_text']
    print(data)
    data = [q['text'] for q in data['keywords']]
    print(data)
    data = ' '.join([str(item) for item in data])
    print(data)

    cursor_cl = coll.find({"class_name": "Class 3", "subject_name": "Mathematics"})
    print(cursor_cl)
    # # ---->
    comb = []
    myList = []
    print(cursor_cl.count())
    conc_weightage = cursor_cl.count()
    if conc_weightage > 0:
        for selected_content_db in cursor_cl:
            match1 = []
            part_kw1 = selected_content_db['keywords'].split(",")
            instruction_id = selected_content_db['sctid']
            filt_semi_kw1 = [let.encode('utf-8') for let in part_kw1]
            contend = ' '.join(filt_semi_kw1)
            print(contend)
            train_set = [contend, data]
            print(train_set)
            tfidf_vectorizer = TfidfVectorizer()
            tfidf_matrix_train = tfidf_vectorizer.fit_transform(train_set)
            cosine_score = cosine_similarity(tfidf_matrix_train)
            cosine_score = cosine_score.tolist()
            print(cosine_score)
            cosine_score = cosine_score[0]
            cosine_score = cosine_score[1]
            parser_iddetails = instruction_id
            parser_score = cosine_score
            myList.append(cosine_score)
            comb.append([instruction_id, cosine_score])
            print(instruction_id)
            print(cosine_score)
            df = pd.DataFrame(comb)
            print(df)
            render_template('result.html', tables=[df.to_html(classes='table', index=False)])

    return 'file upload successful'

@app.route("/getmetaData", methods=['GET'])
def get_document():
    qopts = {'query': ''}
    my_query = discovery.query(environment_id, doc_collection_id, qopts)

    json_it = jsonify(my_query)
    print(type(json_it))
    # return render_template("Json-Result.html", data=json_it)
    return json_it


@app.route("/delete_document", methods=['GET'])
def delete_document():
    for document_id in document_id_list:
        delete_doc = discovery.delete_document(environment_id, doc_collection_id, document_id)
        print(json.dumps(delete_doc, indent=2))
    return json.dumps(delete_doc, indent=2)


port = os.getenv('PORT', '5000')
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(port))