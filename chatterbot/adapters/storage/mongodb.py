from chatterbot.adapters.storage import StorageAdapter
from chatterbot.conversation import Statement, Response
from pymongo import MongoClient
from chatterbot.utils.text_tag import get_tag
from chatterbot.utils.text_tag import get_tag_weight

class Query(object):

    def __init__(self, query={}):
        self.query = query

    def value(self):
        return self.query.copy()

    def raw(self, data):
        query = self.query.copy()

        query.update(data)

        return Query(query)

    def statement_text_equals(self, statement_text):
        query = self.query.copy()

        query['text'] = statement_text

        return Query(query)

    def statement_text_not_in(self, statements):
        query = self.query.copy()

        if 'text' not in query:
            query['text'] = {}

        if '$nin' not in query['text']:
            query['text']['$nin'] = []

        query['text']['$nin'].extend(statements)

        return Query(query)

    def statement_response_list_contains(self, statement_text):
        query = self.query.copy()

        if 'in_response_to' not in query:
            query['in_response_to'] = {}

        if '$elemMatch' not in query['in_response_to']:
            query['in_response_to']['$elemMatch'] = {}

        query['in_response_to']['$elemMatch']['text'] = statement_text

        return Query(query)

    def statement_response_list_equals(self, response_list):
        query = self.query.copy()

        query['in_response_to'] = response_list

        return Query(query)


class MongoDatabaseAdapter(StorageAdapter):
    """
    The MongoDatabaseAdapter is an interface that allows
    ChatterBot to store statements in a MongoDB database.
    """

    def __init__(self, **kwargs):
        super(MongoDatabaseAdapter, self).__init__(**kwargs)

        self.database_name = self.kwargs.get(
            "database", "chatterbot-database"
        )
        self.database_uri = self.kwargs.get(
            "database_uri", "mongodb://localhost:27017/"
        )

        # Use the default host and port
        self.client = MongoClient(self.database_uri)

        # Specify the name of the database
        self.database = self.client[self.database_name]

        # The mongo collection of statement documents
        self.statements = self.database['statements']

        # Set a requirement for the text attribute to be unique
        self.statements.create_index('text', unique=True)

        self.base_query = Query()

    def count(self):
        return self.statements.count()

    def find(self, statement_text):
        query = self.base_query.statement_text_equals(statement_text)

        values = self.statements.find_one(query.value())

        if not values:
            return None

        del(values['text'])

        # Build the objects for the response list
        values['in_response_to'] = self.deserialize_responses(
            values['in_response_to']
        )

        return Statement(statement_text, **values)

    def deserialize_responses(self, response_list):
        """
        Takes the list of response items and returns
        the list converted to Response objects.
        """
        proxy_statement = Statement("")

        for response in response_list:
            text = response["text"]
            del(response["text"])

            proxy_statement.add_response(
                Response(text, **response)
            )

        return proxy_statement.in_response_to

    def mongo_to_object(self, statement_data):
        """
        Return Statement object when given data
        returned from Mongo DB.
        """
        statement_text = statement_data['text']
        del(statement_data['text'])

        statement_data['in_response_to'] = self.deserialize_responses(
            statement_data['in_response_to']
        )

        return Statement(statement_text, **statement_data)

    def filter(self, **kwargs):
        """
        Returns a list of statements in the database
        that match the parameters specified.
        """
        query = self.base_query

        # Convert Response objects to data
        if 'in_response_to' in kwargs:
            serialized_responses = []
            for response in kwargs['in_response_to']:
                serialized_responses.append({'text': response.text})

            query = query.statement_response_list_equals(serialized_responses)
            del(kwargs['in_response_to'])

        if 'in_response_to__contains' in kwargs:
            query = query.statement_response_list_contains(
                kwargs['in_response_to__contains']
            )
            del(kwargs['in_response_to__contains'])

        query = query.raw(kwargs)

        matches = self.statements.find(query.value())

        results = []

        for match in list(matches):
            results.append(self.mongo_to_object(match))

        return results

    def update(self, statement):
        from pymongo import UpdateOne, ReplaceOne

        # Do not alter the database unless writing is enabled
        if not self.read_only:
            data = statement.serialize()

            operations = []

            update_operation = ReplaceOne(
                {'text': statement.text}, data, True
            )
            operations.append(update_operation)

            # Make sure that an entry for each response is saved
            for response in statement.in_response_to:

                # $setOnInsert does nothing if the document is not created
                update_operation = UpdateOne(
                    {'text': response.text},
                    {'$setOnInsert': {'in_response_to': []}},
                    upsert=True
                )
                operations.append(update_operation)

            self.statements.bulk_write(operations, ordered=False)

        return statement

    def get_random(self):
        """
        Returns a random statement from the database
        """
        from random import randint

        count = self.count()

        if count < 1:
            raise self.EmptyDatabaseException()

        random_integer = randint(0, count - 1)

        statements = self.statements.find().limit(1).skip(random_integer)

        return self.mongo_to_object(list(statements)[0])

    def remove(self, statement_text):
        """
        Removes the statement that matches the input text.
        Removes any responses from statements if the response text matches the
        input text.
        """
        for statement in self.filter(in_response_to__contains=statement_text):
            statement.remove_response(statement_text)
            self.update(statement)

        self.statements.delete_one({'text': statement_text})

    def get_response_statements(self, text):
        """
        Return only statements that are in response to another statement.
        A statement must exist which lists the closest matching statement in the
        in_response_to field. Otherwise, the logic adapter may find a closest
        matching statement that does not have a known response.
        """
        tag = get_tag(text)
        andTag = [{'in_response_to': []}]

        for kw in tag:
            andTag.append({'tag': kw})

        _statement_query_tag = {
            '$and': andTag
        }

        _statement_query_tag.update(self.base_query.value())
        if len(tag) != 0:
            response_query = self.statements.find(_statement_query_tag)
            response_query_list = list(response_query)
            # print(tag, response_query_list)
            # 如果标签没有匹配的，可能标签有超过，使用标签diff差最小的一个
            # 最开始是5，这个值越大，越容易匹配错误答案
            if (len(response_query_list) == 0) and (len(tag) >= 3):
                kw_weight = get_tag_weight()
                similar_tag = [{'in_response_to': []}]
                light_tag = []
                for kw in tag:
                    if kw in kw_weight:
                        similar_tag.append({'tag': kw})
                    else:
                        light_tag.append(kw)
                if len(light_tag) > 0:
                    similar_tag.append({'tag': {'$in': light_tag}})

                _statement_query_tag_in = {
                    '$and': similar_tag
                }
                response_query_similar = self.statements.find(_statement_query_tag_in)
                minDiff = int(100)
                minquery = {100: []}

                for statement in response_query_similar:
                    # print(statement)
                    if len(statement['tag']) >= len(tag):
                        tagDiff = len(set(statement['tag']) - set(tag))
                        pDff = tagDiff / len(statement['tag'])
                    else:
                        tagDiff = len(set(tag) - set(statement['tag']))
                        pDff = tagDiff / len(set(tag))
                    if tagDiff <= minDiff:
                        minDiff = tagDiff
                        if not tagDiff in minquery:
                            minquery[tagDiff] = []
                        obj = {'tagDiff': tagDiff,'pDff': pDff, 'text': self.mongo_to_object(statement), 'strict': True}
                        minquery[tagDiff].append(obj)
                # print(minquery)
                return minquery[minDiff]
        else:
            # 如果一个标签都没有命中，表示没有什么意义
            response_query_list = []
        statement_o = []
        
        for statement in response_query_list:
            if len(statement['tag']) >= len(tag):
                tagDiff = set(statement['tag']) - set(tag)
                pDff = len(tagDiff) / len(statement['tag'])
            else:
                tagDiff = set(tag) - set(statement['tag'])
                pDff = len(tagDiff) / len(set(tag))
            obj = {'tagDiff': len(tagDiff),'pDff': pDff, 'text': self.mongo_to_object(statement)}
            statement_o.append(obj)

        return statement_o

        # 原始逻辑
        # _statement_query = {
        #     'text': {
        #         '$in': response_query
        #     }
        # }

        # _statement_query.update(self.base_query.value())

        # statement_query = self.statements.find(_statement_query)

        # statement_objects = []

        # for statement in list(statement_query):
        #     statement_objects.append(self.mongo_to_object(statement))

        # return statement_objects

    def drop(self):
        """
        Remove the database.
        """
        self.client.drop_database(self.database_name)
