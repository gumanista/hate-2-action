export interface Message {
  message_id: number;
  user_id: number;
  user_username: string;
  chat_title: string | null;
  text: string;
}